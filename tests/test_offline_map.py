import json
import re
import math
import unittest
from pathlib import Path

from biqmapa.offline_map import projected_bounds, validate_extent


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
