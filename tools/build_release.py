"""Build and verify one native TURN THE PAGE beta on its host OS."""
from __future__ import annotations

import os
from pathlib import Path
import platform
import plistlib
import shutil
import subprocess
import sys
import tarfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from settings import ARCHIVE_NAME, BUNDLE_ID, TITLE, VERSION

DIST = ROOT / "dist"
BUILD = ROOT / "build" / "pyinstaller"
RELEASE = ROOT / "release"


def run(*args, env=None):
    subprocess.run([str(arg) for arg in args], cwd=ROOT, check=True, env=env)


def clean_target(path):
    if path.exists():
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()


def build():
    system = platform.system()
    BUILD.parent.mkdir(parents=True, exist_ok=True)
    icon = ROOT / "packaging" / {
        "Darwin": "app-icon.icns", "Windows": "app-icon.ico",
    }.get(system, "app-icon.png")
    separator = ";" if system == "Windows" else ":"
    args = [
        sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
        "--windowed", "--onedir", "--name", TITLE,
        "--icon", icon, "--add-data", f"{ROOT/'assets'}{separator}assets",
        "--add-data", f"{ROOT/'packaging'}{separator}packaging",
        "--distpath", DIST, "--workpath", BUILD,
        "--specpath", ROOT / "build", ROOT / "main.py",
    ]
    if system == "Darwin":
        args[args.index("--icon"):args.index("--icon")] = [
            "--osx-bundle-identifier", BUNDLE_ID,
        ]
        for candidate in (Path("/opt/homebrew/lib/libSDL3.dylib"),
                          Path("/usr/local/lib/libSDL3.dylib")):
            if candidate.exists():
                args[args.index("--distpath"):args.index("--distpath")] = [
                    "--add-binary", f"{candidate}{separator}.",
                ]
                break
    env = dict(os.environ, PYINSTALLER_CONFIG_DIR=str(ROOT/"build"/"pyinstaller-config"))
    run(*args, env=env)
    return system


def verify(system):
    executable = {
        "Darwin": DIST / f"{TITLE}.app" / "Contents" / "MacOS" / TITLE,
        "Windows": DIST / TITLE / f"{TITLE}.exe",
    }.get(system, DIST / TITLE / TITLE)
    report = ROOT / "build" / f"bundle-{system.lower()}.json"
    env = dict(os.environ, SDL_VIDEODRIVER="dummy", SDL_AUDIODRIVER="dummy")
    run(executable, "--verify-bundle", report, env=env)
    if not report.exists():
        raise RuntimeError("Packaged runtime did not produce its verification report")


def package(system):
    RELEASE.mkdir(parents=True, exist_ok=True)
    label = {"Darwin": "macOS", "Windows": "Windows"}.get(system, "Linux")
    archive = RELEASE / f"{ARCHIVE_NAME}-{label}-{VERSION}"
    zip_archive = Path(f"{archive}.zip")
    tar_archive = Path(f"{archive}.tar.gz")
    target = DIST / (f"{TITLE}.app" if system == "Darwin" else TITLE)
    clean_target(zip_archive)
    clean_target(tar_archive)
    if system == "Darwin":
        plist = target / "Contents" / "Info.plist"
        metadata = plistlib.loads(plist.read_bytes())
        clean_version = VERSION.split("-")[0]
        metadata["CFBundleShortVersionString"] = clean_version
        metadata["CFBundleVersion"] = clean_version
        metadata["LSApplicationCategoryType"] = "public.app-category.action-games"
        metadata["NSHighResolutionCapable"] = True
        plist.write_bytes(plistlib.dumps(metadata))
        run("codesign", "--force", "--deep", "--sign", "-", target)
        run("codesign", "--verify", "--deep", "--strict", target)
        run("ditto", "-c", "-k", "--sequesterRsrc", "--keepParent", target,
            zip_archive)
        return zip_archive
    if system == "Windows":
        with zipfile.ZipFile(zip_archive, "w",
                             zipfile.ZIP_DEFLATED, compresslevel=9) as output:
            for file in target.rglob("*"):
                if file.is_file():
                    output.write(file, Path(TITLE) / file.relative_to(target))
        return zip_archive
    with tarfile.open(tar_archive, "w:gz") as output:
        output.add(target, arcname=TITLE)
    return tar_archive


if __name__ == "__main__":
    clean_target(DIST)
    clean_target(BUILD)
    native = build()
    verify(native)
    print(package(native))
