import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from biqmapa.smoke import run

if __name__ == "__main__":
    raise SystemExit(run(Path(sys.argv[1]) if len(sys.argv) > 1 else Path("build/smoke.json")))
