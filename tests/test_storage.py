import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from biqmapa.storage import Store


def empty_state():
    return dict(version=1, properties=[], blocks=[], lots=[], history=[], notices=[], originHistory=[])


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.temp.name))

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def test_starts_without_properties(self):
        self.assertIsNone(self.store.load())

    def test_persists_after_reopening(self):
        state = empty_state()
        state["properties"] = [dict(cim="101", nome="CADASTRO FICTÍCIO")]
        self.store.save(json.dumps(state))
        self.store.close()
        self.store = Store(Path(self.temp.name))
        self.assertEqual(self.store.load(), state)

    def test_invalid_update_preserves_previous_state(self):
        self.store.save(json.dumps(empty_state()))
        bad = empty_state()
        bad["properties"] = [dict(cim="101"), dict(cim="101")]
        with self.assertRaises(ValueError):
            self.store.save(json.dumps(bad))
        self.assertEqual(self.store.load(), empty_state())

    def test_backup_contains_state_before_first_daily_update(self):
        initial = empty_state()
        self.store.save(json.dumps(initial))
        changed = empty_state()
        changed["properties"] = [dict(cim="101")]
        self.store.save(json.dumps(changed))
        backups = list(self.store.backups.glob("*.sqlite3"))
        self.assertEqual(len(backups), 1)
        with sqlite3.connect(backups[0]) as connection:
            saved = json.loads(connection.execute("SELECT payload FROM app_state").fetchone()[0])
        self.assertEqual(saved, initial)

    def test_refuses_orphan_lot(self):
        state = empty_state()
        state["lots"] = [dict(cim="101", blockId="missing")]
        with self.assertRaises(ValueError):
            self.store.save(json.dumps(state))


if __name__ == "__main__":
    unittest.main()
