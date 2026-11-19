import json
import logging
import mimetypes
import sys
from pathlib import Path

from PySide6.QtCore import QByteArray, QBuffer, QIODevice, QObject, QSettings, QTimer, QUrl, Qt, Slot
from PySide6.QtGui import QAction, QDesktopServices, QIcon
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtPrintSupport import QPrintDialog, QPrinter
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineCore import (
    QWebEnginePage, QWebEngineProfile, QWebEngineSettings,
    QWebEngineUrlRequestInterceptor, QWebEngineUrlScheme, QWebEngineUrlSchemeHandler,
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QApplication, QFileDialog, QMainWindow, QMessageBox

from . import __version__
from .storage import Store, data_directory

ASSETS = Path(__file__).parent / "assets"
APP_URL = "biqmapa://app/index.html"


def register_scheme():
    scheme = QWebEngineUrlScheme(b"biqmapa")
    scheme.setSyntax(QWebEngineUrlScheme.Syntax.Host)
    scheme.setFlags(QWebEngineUrlScheme.Flag.SecureScheme | QWebEngineUrlScheme.Flag.LocalScheme | QWebEngineUrlScheme.Flag.LocalAccessAllowed)
    QWebEngineUrlScheme.registerScheme(scheme)


class AssetsHandler(QWebEngineUrlSchemeHandler):
    def requestStarted(self, job):
        name = job.requestUrl().path().lstrip("/") or "index.html"
        if job.requestUrl().host() != "app" or name not in {"index.html", "brasao.png", "imovel-padrao.webp", "biqmapa.ico", "biqmapa.png"}:
            job.fail(job.Error.UrlNotFound)
            return
        buffer = QBuffer(job)
        buffer.setData(QByteArray((ASSETS / name).read_bytes()))
        buffer.open(QIODevice.OpenModeFlag.ReadOnly)
        job.reply((mimetypes.guess_type(name)[0] or "application/octet-stream").encode("ascii"), buffer)


class NetworkPolicy(QWebEngineUrlRequestInterceptor):
    def interceptRequest(self, info):
        url = info.requestUrl()
        if url.scheme() in ("biqmapa", "qrc", "data", "blob", "about"):
            return
        allowed_tile = (
            url.scheme() == "https" and url.host() == "services.arcgisonline.com"
            and url.path().lower().startswith("/arcgis/rest/services/world_imagery/mapserver/tile/")
            and bytes(info.requestMethod()) == b"GET"
        )
        if not allowed_tile:
            info.block(True)


class AppPage(QWebEnginePage):
    def acceptNavigationRequest(self, url, navigation_type, is_main_frame):
        if url.scheme() == "biqmapa" and url.host() == "app":
            return True
        if url.scheme() == "blob":
            return True
        if is_main_frame and url.scheme() == "https":
            QDesktopServices.openUrl(url)
        return False


class Bridge(QObject):
    def __init__(self, store, parent=None):
        super().__init__(parent)
        self.store = store

    @Slot(result=str)
    def load_state(self):
        try:
            return json.dumps({"ok": True, "state": self.store.load()}, ensure_ascii=False)
        except Exception:
            logging.exception("Erro ao abrir a base local")
            return json.dumps({"ok": False, "error": "Não foi possível abrir a base local. Seus arquivos foram preservados."})

    @Slot(str, result=str)
    def save_state(self, payload):
        try:
            self.store.save(payload)
            return '{"ok":true}'
        except Exception:
            logging.exception("Erro ao salvar a base local")
            return json.dumps({"ok": False, "error": "Não foi possível salvar. Exporte um backup antes de fechar."})

    @Slot(result=str)
    def environment(self):
        return json.dumps({"version": __version__, "directory": str(self.store.directory)}, ensure_ascii=False)


class Window(QMainWindow):
    def __init__(self, store):
        super().__init__()
        self.store = store
        self.setWindowTitle(f"BIQMapa {__version__} — Mapeamento Urbano")
        self.setWindowIcon(QIcon(str(ASSETS / "biqmapa.ico")))
        self.resize(1440, 900)
        self.setMinimumSize(980, 650)
        self.profile = QWebEngineProfile("BIQMapa", self)
        self.profile.setPersistentStoragePath(str(store.directory / "interface"))
        self.profile.setCachePath(str(store.directory / "cache"))
        self.profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.MemoryHttpCache)
        self.handler = AssetsHandler(self.profile)
        self.profile.installUrlSchemeHandler(b"biqmapa", self.handler)
        self.network_policy = NetworkPolicy(self.profile)
        self.profile.setUrlRequestInterceptor(self.network_policy)
        self.view = QWebEngineView(self)
        self.page = AppPage(self.profile, self.view)
        self.view.setPage(self.page)
        self.page.settings().setAttribute(QWebEngineSettings.WebAttribute.FullScreenSupportEnabled, True)
        self.channel = QWebChannel(self.page)
        self.bridge = Bridge(store, self.channel)
        self.channel.registerObject("desktop", self.bridge)
        self.page.setWebChannel(self.channel)
        self.setCentralWidget(self.view)
        self.profile.downloadRequested.connect(self.download)
        self.view.printRequested.connect(self.print_document)
        self.page.fullScreenRequested.connect(self.fullscreen)
        self.view.loadFinished.connect(self.loaded)
        self.settings = QSettings("LucasCezar", "BIQMapa")
        geometry = self.settings.value("windowGeometry")
        if geometry:
            self.restoreGeometry(geometry)
        self._closing = False
        self._allow_close = False
        self._printer = None
        self.view.printFinished.connect(self.print_finished)
        self.view.setUrl(QUrl(APP_URL))

    def loaded(self, ok):
        if not ok:
            QMessageBox.critical(self, "BIQMapa", "Não foi possível carregar a interface. Reinstale o aplicativo. Os dados locais serão preservados.")

    def download(self, request):
        name = Path(request.suggestedFileName()).name or "BIQMapa-Exportacao.json"
        path, _ = QFileDialog.getSaveFileName(self, "Salvar arquivo", str(Path.home() / "Downloads" / name))
        if not path:
            request.cancel()
            return
        target = Path(path)
        request.setDownloadDirectory(str(target.parent))
        request.setDownloadFileName(target.name)
        request.accept()

    def print_document(self):
        if self._printer is not None:
            return
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        dialog = QPrintDialog(printer, self)
        if dialog.exec() == QPrintDialog.DialogCode.Accepted:
            self._printer = printer
            self.view.print(printer)

    def print_finished(self, ok):
        self._printer = None
        if not ok:
            QMessageBox.warning(self, "Impressão", "A impressão não foi concluída.")

    def fullscreen(self, request):
        request.accept()
        if request.toggleOn():
            self.showFullScreen()
        else:
            self.showNormal()

    def closeEvent(self, event):
        if self._allow_close:
            self.settings.setValue("windowGeometry", self.saveGeometry())
            event.accept()
            return
        event.ignore()
        if self._closing:
            return
        self._closing = True
        self.page.runJavaScript("typeof desktopCanClose === 'function' ? desktopCanClose() : false", self.check_close)

    def check_close(self, result):
        self._closing = False
        if result:
            self._allow_close = True
            self.close()
        else:
            answer = QMessageBox.question(self, "Fechar o BIQMapa", "Há um desenho ou uma operação em andamento, ou a interface não respondeu. Fechar mesmo assim? O desenho ainda não confirmado será perdido.")
            if answer == QMessageBox.StandardButton.Yes:
                self._allow_close = True
                self.close()


def main():
    if "--smoke-test" in sys.argv:
        from .smoke import run
        return run(Path(sys.argv[sys.argv.index("--smoke-test") + 1]))
    register_scheme()
    app = QApplication(sys.argv)
    app.setOrganizationName("LucasCezar")
    app.setApplicationName("BIQMapa")
    app.setApplicationVersion(__version__)
    directory = data_directory()
    directory.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(filename=directory / "biqmapa.log", level=logging.WARNING, format="%(asctime)s %(levelname)s %(message)s")
    lock = QLocalServer(app)
    socket = QLocalSocket()
    socket.connectToServer("BIQMapa-" + str(directory).replace("\\", "_").replace("/", "_"))
    if socket.waitForConnected(300):
        socket.write(b"open")
        socket.waitForBytesWritten(300)
        QMessageBox.information(None, "BIQMapa", "O BIQMapa já está aberto neste usuário do Windows.")
        return 0
    name = "BIQMapa-" + str(directory).replace("\\", "_").replace("/", "_")
    QLocalServer.removeServer(name)
    if not lock.listen(name):
        QMessageBox.critical(None, "BIQMapa", "Não foi possível iniciar uma sessão exclusiva.")
        return 1
    try:
        store = Store(directory)
        store.load()
    except Exception:
        logging.exception("Erro ao iniciar o armazenamento")
        QMessageBox.critical(None, "BIQMapa", "Não foi possível abrir os dados locais. Os arquivos existentes foram preservados.")
        return 1
    window = Window(store)
    window.show()
    def activate():
        client = lock.nextPendingConnection()
        if client:
            client.deleteLater()
        window.showNormal()
        window.raise_()
        window.activateWindow()
    lock.newConnection.connect(activate)
    result = app.exec()
    window.view.setPage(QWebEnginePage(window.view))
    window.page.deleteLater()
    app.sendPostedEvents(None, 0)
    store.close()
    return result
