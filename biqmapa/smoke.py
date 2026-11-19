import json
import sys
import tempfile
import time
from pathlib import Path

from PySide6.QtCore import QCoreApplication, QEvent, QTimer
from PySide6.QtWebEngineCore import QWebEnginePage
from PySide6.QtWidgets import QApplication

from .desktop import Window, register_scheme
from .storage import Store


def run(result_path: Path) -> int:
    register_scheme()
    app = QApplication.instance() or QApplication(sys.argv[:1])
    temporary = tempfile.TemporaryDirectory(prefix="biqmapa-test-")
    store = Store(Path(temporary.name))
    window = Window(store)
    window.show()
    started = time.monotonic()
    phase = "initial"
    result = {"ok": False}

    def finish(ok, error=""):
        result.update(ok=ok, error=error)
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        window._allow_close = True
        window.close()
        app.quit()

    def poll():
        if time.monotonic() - started > 50:
            finish(False, "A interface não concluiu a verificação no prazo.")
            return
        window.page.runJavaScript("JSON.stringify({ready:typeof desktopReady!=='undefined'&&desktopReady,count:typeof state!=='undefined'&&state?state.properties.length:null,phase:window.__smokePhase||'',error:window.__smokeError||''})", inspect)

    def inspect(raw):
        nonlocal phase
        try:
            status = json.loads(raw or "{}")
            if status.get("error"):
                finish(False, status["error"])
                return
            if not status.get("ready"):
                QTimer.singleShot(200, poll)
                return
            if phase == "initial":
                assert status["count"] == 0, "A instalação precisa começar vazia."
                phase = "import"
                window.page.runJavaScript("""
                (async()=>{try{
                  page='imports';render();
                  const rows=[{cim:'000101',nome:'CADASTRO DE TESTE A',quadra:'08',lote:'03',situacao:'Ativo'},{cim:'102',nome:'CADASTRO DE TESTE B',quadra:'8',lote:'3',situacao:'Excluído logicamente'}];
                  const transfer=new DataTransfer();transfer.items.add(new File([JSON.stringify({format:'tributos-docs-imoveis',version:1,properties:rows})],'teste.json',{type:'application/json'}));
                  document.querySelector('#importFile').files=transfer.files;
                  await reviewImport();
                  if(pendingImport?.added.length!==2)throw Error('Falha na análise do JSON.');
                  await applyImport();
                  if(prop('101').status!=='ativo'||prop('102').status!=='excluido')throw Error('Situação cadastral incorreta.');
                  await commit(()=>{state.blocks.push({id:'test-block',number:'08',space:'geo',points:[[100,100],[300,100],[300,300],[100,300]]});state.lots.push({id:'test-lot',blockId:'test-block',cim:'101',points:[[110,110],[200,110],[200,200],[110,200]]})});
                  window.__smokePhase='saved';
                }catch(e){window.__smokeError=String(e)}})();
                """)
            elif phase == "import" and status.get("phase") == "saved":
                saved = store.load()
                assert len(saved["properties"]) == 2
                assert len(saved["lots"]) == 1
                phase = "reload"
                window.view.reload()
                QTimer.singleShot(500, poll)
                return
            elif phase == "reload" and status["count"] == 2 and status.get("phase") == "":
                result.update(empty_start=True, import_json=True, status_import=True, sqlite_persistence=True, reload=True)
                finish(True)
                return
            QTimer.singleShot(200, poll)
        except Exception as error:
            finish(False, str(error))

    QTimer.singleShot(300, poll)
    app.exec()
    window.view.setPage(QWebEnginePage(window.view))
    window.page.deleteLater()
    window.profile.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    store.close()
    return 0 if result["ok"] else 1
