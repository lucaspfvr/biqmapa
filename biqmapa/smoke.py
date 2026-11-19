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
    window.resize(1366, 768)
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
        if time.monotonic() - started > 120:
            finish(False, "A interface não concluiu a verificação no prazo.")
            return
        window.page.runJavaScript("""JSON.stringify((()=>{const b=document.querySelector('#basemapSvg'),c=document.querySelector('#satelliteTiles'),nodes=c?[...c.children]:[],front=c?[...(c.foregroundTileKeys||[])]:[],map=document.querySelector('#map')?.getBoundingClientRect(),main=document.querySelector('#main')?.getBoundingClientRect(),summary=document.querySelector('#mapNavSummary')?.getBoundingClientRect();return {ready:typeof desktopReady!=='undefined'&&desktopReady,count:typeof state!=='undefined'&&state?state.properties.length:null,phase:window.__smokePhase||'',error:window.__smokeError||'',kind:b?.dataset.kind,front:front.length,loaded:front.filter(k=>nodes.some(n=>n.dataset.tile===k&&n.dataset.loaded==='1')).length,detail:Math.max(0,...nodes.map(n=>Number(n.dataset.actualZoom)||0)),mapTop:map?.top,mainTop:main?.top,mapHeight:map?.height,mainHeight:main?.height,summaryTop:summary?.top,mapStatus:document.querySelector('#mapStatus')?.textContent}})())""", inspect)

    def inspect(raw):
        nonlocal phase
        try:
            status = json.loads(raw or "{}")
            result["last_status"] = status
            if status.get("error"):
                finish(False, status["error"])
                return
            if not status.get("ready"):
                QTimer.singleShot(200, poll)
                return
            if phase == "initial":
                assert status["count"] == 0, "A instalação precisa começar vazia."
                phase = "satellite"
                window.page.runJavaScript("camera={x:GEO.width/2-500,y:GEO.height/2-350,w:1000,h:700};drawSvg()")
            elif phase == "satellite" and status.get("kind") == "satellite" and status.get("front", 0) > 0 and status.get("front") == status.get("loaded"):
                assert status["detail"] >= 18, "O mapa não carregou o nível de detalhe necessário."
                assert status["mapTop"] - status["mainTop"] <= 18, "O cabeçalho ainda ocupa a altura do mapa."
                assert status["mapHeight"] >= status["mainHeight"] - 40
                assert status["summaryTop"] < status["mapTop"]
                result.update(satellite_tiles=True, high_resolution_zoom=True, taller_map=True, navigation_summary=True)
                result_path.parent.mkdir(parents=True, exist_ok=True)
                window.view.grab().save(str(result_path.with_name(result_path.stem + "-map.png")))
                phase = "offline"
                window.page.runJavaScript("Object.defineProperty(navigator,'onLine',{configurable:true,get:()=>false});drawSvg()")
            elif phase == "offline":
                assert status.get("kind") == "satellite", "Os trechos carregados desapareceram na simulação offline."
                result["session_cache"] = True
                phase = "import"
                window.page.runJavaScript("""
                (async()=>{try{
                  delete navigator.onLine;retrySatellite();page='properties';render();page='map';render();if(!document.querySelector('#satelliteTiles [data-loaded=\"1\"]'))throw Error('O satélite desapareceu ao trocar de tela.');
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
