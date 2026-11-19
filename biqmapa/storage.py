import json
import os
import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path


def data_directory() -> Path:
    if os.name == "nt":
        return Path(os.environ["LOCALAPPDATA"]) / "BIQMapa"
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")) / "BIQMapa"


def validate_state(state: dict) -> None:
    if not isinstance(state, dict) or state.get("version") != 1:
        raise ValueError("Formato de dados incompatível.")
    for field in ("properties", "blocks", "lots", "history", "notices", "originHistory"):
        if not isinstance(state.get(field), list):
            raise ValueError(f"Campo inválido: {field}.")
    identifiers = set()
    for item in state["properties"]:
        cim = item.get("cim") if isinstance(item, dict) else None
        if not isinstance(cim, str) or not cim or cim in identifiers:
            raise ValueError("Cadastro sem CIM ou com CIM repetido.")
        identifiers.add(cim)
    block_ids = {b.get("id") for b in state["blocks"] if isinstance(b, dict)}
    linked = set()
    for lot in state["lots"]:
        if not isinstance(lot, dict) or lot.get("blockId") not in block_ids or lot.get("cim") not in identifiers:
            raise ValueError("Lote vinculado a um cadastro ou quadra inexistente.")
        if lot["cim"] in linked:
            raise ValueError("Um imóvel não pode ter duas demarcações.")
        linked.add(lot["cim"])


class Store:
    def __init__(self, directory: Path | None = None):
        self.directory = directory or data_directory()
        self.directory.mkdir(parents=True, exist_ok=True)
        self.path = self.directory / "biqmapa.sqlite3"
        self.backups = self.directory / "backups"
        self.connection = sqlite3.connect(self.path)
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.execute("PRAGMA synchronous=FULL")
        self.connection.execute("CREATE TABLE IF NOT EXISTS app_state (id INTEGER PRIMARY KEY CHECK(id=1), payload TEXT NOT NULL, updated_at TEXT NOT NULL)")
        self.connection.commit()
        self._backup_date = None

    def load(self):
        row = self.connection.execute("SELECT payload FROM app_state WHERE id=1").fetchone()
        if row is None:
            return None
        state = json.loads(row[0])
        validate_state(state)
        return state

    def save(self, payload: str) -> None:
        if len(payload.encode("utf-8")) > 256 * 1024 * 1024:
            raise ValueError("A base ultrapassou o limite de 256 MB desta versão.")
        state = json.loads(payload)
        validate_state(state)
        today = datetime.now().date().isoformat()
        if self._backup_date != today and self.connection.execute("SELECT 1 FROM app_state WHERE id=1").fetchone():
            self.backup()
            self._backup_date = today
        with self.connection:
            self.connection.execute(
                "INSERT INTO app_state (id,payload,updated_at) VALUES (1,?,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload, updated_at=excluded.updated_at",
                (payload, datetime.now().isoformat(timespec="seconds")),
            )

    def backup(self) -> Path:
        self.backups.mkdir(exist_ok=True)
        destination = self.backups / f"BIQMapa-{datetime.now():%Y-%m-%d-%H%M%S-%f}.sqlite3"
        temporary = destination.with_suffix(".tmp")
        try:
            with closing(sqlite3.connect(temporary)) as target:
                self.connection.backup(target)
            temporary.replace(destination)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise
        for old in sorted(self.backups.glob("BIQMapa-*.sqlite3"), reverse=True)[30:]:
            old.unlink()
        return destination

    def close(self):
        self.connection.close()
