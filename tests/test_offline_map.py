import json
import re
import math
import unittest
import hashlib
import tempfile
from pathlib import Path
from unittest.mock import patch

from biqmapa.offline_map import OfflineMap, projected_bounds, validate_extent


class MapReferenceTests(unittest.TestCase):
    def setUp(self):
        text = (Path(__file__).parents[1] / "biqmapa/assets/index.html").read_text(encoding="utf-8")
        self.reference = json.loads(re.search(r'<script id="seed" type="application/json">(.*?)</script>', text, re.S)[1])["mapData"]

    def test_bounds_match_the_original_satellite_extent(self):
        bounds = projected_bounds(self.reference)
        self.assertAlmostEqual(bounds[0], 6378137 * math.radians(self.reference["bbox"][0]), places=4)
        self.assertAlmostEqual(bounds[2], 6378137 * math.radians(self.reference["bbox"][2]), places=4)
        extent = dict(zip(("xmin", "ymin", "xmax", "ymax"), bounds))
        extent["spatialReference"] = {"latestWkid": 3857}
        validate_extent(extent, self.reference)

    def test_refuses_a_shifted_image(self):
        bounds = projected_bounds(self.reference)
        extent = dict(zip(("xmin", "ymin", "xmax", "ymax"), bounds))
        extent["xmin"] += 100
        extent["spatialReference"] = {"latestWkid": 3857}
        with self.assertRaises(ValueError):
            validate_extent(extent, self.reference)

    def test_reuses_a_prepared_copy_without_network(self):
        data = b"\xff\xd8\xff\xc0\x00\x11\x08" + (3106).to_bytes(2, "big") + (4096).to_bytes(2, "big") + b"\x03\x01\x11\x00\x02\x11\x00\x03\x11\x00\xff\xd9"
        with tempfile.TemporaryDirectory() as temporary:
            manager = OfflineMap(Path(temporary), self.reference)
            try:
                manager.directory.mkdir()
                digest = hashlib.sha256(data).hexdigest()
                extent = dict(zip(("xmin", "ymin", "xmax", "ymax"), projected_bounds(self.reference)))
                extent["spatialReference"] = {"wkid": 3857}
                metadata = dict(version=1, width=4096, height=3106, reference=manager.reference, extent=extent, sha256=digest)
                (manager.directory / (digest + ".jpg")).write_bytes(data)
                (manager.directory / "biquinhas-4k.json").write_text(json.dumps(metadata), encoding="utf-8")
                with patch("biqmapa.offline_map.urllib.request.urlopen", side_effect=AssertionError("O cache pronto não deve acessar a internet.")):
                    prepared = manager.prepare()
                self.assertEqual(prepared["sha256"], digest)
                self.assertTrue(prepared["data"].startswith("data:image/jpeg;base64,"))
            finally:
                manager.close()
