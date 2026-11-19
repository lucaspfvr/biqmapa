import base64
import hashlib
import json
import math
import re
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

SERVICE = "https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer"
CREDIT = "© Esri, Vantor, Earthstar Geographics e GIS User Community. Imagem estática para uso interno; direitos reservados aos fornecedores."


def projected_bounds(reference):
    unit = 2 * math.pi * 6378137 / (256 * 2 ** reference["baseZoom"])
    half = math.pi * 6378137
    xmin = reference["origin"][0] * unit - half
    ymax = half - reference["origin"][1] * unit
    return [xmin, ymax - reference["height"] * unit, xmin + reference["width"] * unit, ymax]


def validate_extent(extent, reference):
    if extent.get("spatialReference", {}).get("latestWkid", extent.get("spatialReference", {}).get("wkid")) not in (3857, 102100):
        raise ValueError("A imagem usa outra projeção.")
    actual = [extent.get(k) for k in ("xmin", "ymin", "xmax", "ymax")]
    if any(not isinstance(v, (int, float)) or not math.isfinite(v) for v in actual):
        raise ValueError("A extensão da imagem é inválida.")
    if any(abs(a - b) > 3 for a, b in zip(actual, projected_bounds(reference))):
        raise ValueError("A imagem não corresponde ao recorte de Biquinhas.")


def jpeg_dimensions(data):
    offset = 2
    while offset + 4 < len(data):
        if data[offset] != 255:
            offset += 1
            continue
        while offset < len(data) and data[offset] == 255:
            offset += 1
        if offset >= len(data):
            break
        marker = data[offset]
        offset += 1
        if marker in (1, 216, 217) or 208 <= marker <= 215:
            continue
        length = int.from_bytes(data[offset:offset + 2], "big")
        if length < 2:
            break
        if marker in (192, 193, 194, 195, 197, 198, 199, 201, 202, 203, 205, 206, 207):
            return int.from_bytes(data[offset + 5:offset + 7], "big"), int.from_bytes(data[offset + 3:offset + 5], "big")
        offset += length
    raise ValueError("Dimensões JPEG não encontradas.")


class OfflineMap:
    def __init__(self, directory: Path, reference):
        self.directory = directory / "mapas"
        self.reference = {k: reference[k] for k in ("version", "baseZoom", "origin", "width", "height")}
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="mapa-local")
        self.future = None

    def start(self, refresh=False):
        if self.future is None or (self.future.done() and (refresh or self.future.exception() is not None)):
            self.future = self.executor.submit(self.prepare, refresh)

    def status(self):
        if self.future is None:
            return {"ok": False, "error": "A preparação da imagem ainda não foi iniciada."}
        if not self.future.done():
            return {"ok": True, "ready": False}
        try:
            return {"ok": True, "ready": True, "image": self.future.result()}
        except Exception:
            return {"ok": False, "error": "Não foi possível preparar a imagem local. Confira a conexão e tente novamente; a cópia anterior foi preservada."}

    def prepare(self, refresh=False):
        self.directory.mkdir(parents=True, exist_ok=True)
        manifest = self.directory / "biquinhas-4k.json"
        if manifest.exists() and not refresh:
            try:
                metadata = json.loads(manifest.read_text(encoding="utf-8"))
                assert metadata["reference"] == self.reference
                assert re.fullmatch(r"[a-f0-9]{64}", metadata["sha256"])
                validate_extent(metadata["extent"], self.reference)
                path = self.directory / (metadata["sha256"] + ".jpg")
                data = path.read_bytes()
                assert hashlib.sha256(data).hexdigest() == metadata["sha256"]
                assert jpeg_dimensions(data) == (metadata["width"], metadata["height"])
                return dict(metadata, data="data:image/jpeg;base64," + base64.b64encode(data).decode("ascii"))
            except (OSError, ValueError, KeyError, AssertionError):
                pass
        bounds = projected_bounds(self.reference)
        height = round(4096 * self.reference["height"] / self.reference["width"])
        params = urllib.parse.urlencode(dict(
            f="json", bbox=",".join(map(str, bounds)), bboxSR=3857, imageSR=3857,
            size=f"4096,{height}", format="jpg", transparent="false", dpi=96, compressionQuality=100,
        ))
        request = urllib.request.Request(SERVICE + "/export?" + params, headers={"User-Agent": "BIQMapa/0.7.2"})
        with urllib.request.urlopen(request, timeout=45) as response:
            exported = json.load(response)
        if "error" in exported or exported.get("width") != 4096 or exported.get("height") != height:
            raise ValueError("A exportação não retornou a dimensão esperada.")
        validate_extent(exported["extent"], self.reference)
        url = urllib.parse.urlparse(exported["href"])
        if url.scheme != "https" or url.hostname != "services.arcgisonline.com":
            raise ValueError("Origem da imagem não reconhecida.")
        with urllib.request.urlopen(exported["href"], timeout=45) as response:
            data = response.read(32 * 1024 * 1024 + 1)
        if len(data) > 32 * 1024 * 1024 or not data.startswith(b"\xff\xd8"):
            raise ValueError("Arquivo de imagem inválido.")
        if jpeg_dimensions(data) != (4096, height):
            raise ValueError("A imagem recebida tem dimensões diferentes da exportação.")
        digest = hashlib.sha256(data).hexdigest()
        metadata = dict(version=1, width=4096, height=height, extent=exported["extent"], reference=self.reference,
                        prepared=datetime.now(timezone.utc).isoformat(), sha256=digest, credit=CREDIT,
                        source=SERVICE, captureDates=[])
        try:
            query = urllib.parse.urlencode(dict(f="json", geometry=",".join(map(str, bounds)),
                geometryType="esriGeometryEnvelope", inSR=3857, spatialRel="esriSpatialRelIntersects",
                outFields="SRC_DATE", returnGeometry="false"))
            with urllib.request.urlopen(SERVICE + "/10/query?" + query, timeout=15) as response:
                sources = json.load(response)
            dates = {str(f["attributes"]["SRC_DATE"]) for f in sources.get("features", [])}
            metadata["captureDates"] = sorted(d[:4] + "-" + d[4:6] + "-" + d[6:] for d in dates if len(d) == 8 and d.isdigit())
        except (OSError, ValueError, KeyError):
            pass
        image_path = self.directory / (digest + ".jpg")
        temporary = image_path.with_suffix(".tmp")
        temporary.write_bytes(data)
        temporary.replace(image_path)
        pending = manifest.with_suffix(".tmp")
        pending.write_text(json.dumps(metadata, ensure_ascii=False), encoding="utf-8")
        pending.replace(manifest)
        return dict(metadata, data="data:image/jpeg;base64," + base64.b64encode(data).decode("ascii"))

    def close(self):
        self.executor.shutdown(wait=True, cancel_futures=True)
