import hashlib
import importlib.metadata
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from biqmapa import __version__


def build():
    if os.name != "nt":
        raise SystemExit("Execute a montagem no Windows.")
    os.chdir(ROOT)
    command = [
        sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onedir", "--windowed",
        "--name", "BIQMapa", "--icon", "biqmapa/assets/biqmapa.ico",
        "--add-data", "biqmapa/assets;biqmapa/assets",
        "--collect-submodules", "biqmapa", "main.py",
    ]
    subprocess.run(command, check=True)
    destination = ROOT / "dist" / "BIQMapa"
    shutil.copy2(ROOT / "THIRD_PARTY.md", destination)
    licenses = destination / "licencas"
    licenses.mkdir(exist_ok=True)
    for package in ("PySide6", "PySide6_Essentials", "PySide6_Addons", "shiboken6"):
        distribution = importlib.metadata.distribution(package)
        for file in distribution.files or []:
            if "licenses" in file.parts or "license" in file.name.lower() or "copying" in file.name.lower():
                source = Path(distribution.locate_file(file))
                if source.is_file():
                    target = licenses / package / Path(*file.parts[1:])
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, target)
    python_license = Path(sys.base_prefix) / "LICENSE.txt"
    if python_license.exists():
        shutil.copy2(python_license, licenses / "Python-LICENSE.txt")
    nsis = shutil.which("makensis") or str(Path(os.environ.get("ProgramFiles(x86)", "C:/Program Files (x86)")) / "NSIS/makensis.exe")
    if not Path(nsis).exists():
        raise SystemExit("NSIS não encontrado.")
    output = ROOT / "release" / f"BIQMapa-Setup-{__version__}.exe"
    output.parent.mkdir(exist_ok=True)
    subprocess.run([nsis, f"/DAPP_VERSION={__version__}", f"/DSOURCE_DIR={destination}", f"/DOUTPUT_FILE={output}", str(ROOT / "installer/biqmapa.nsi")], check=True)
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    output.with_suffix(".exe.sha256").write_text(f"{digest}  {output.name}\n", encoding="utf-8")
    print(output)


if __name__ == "__main__":
    build()
