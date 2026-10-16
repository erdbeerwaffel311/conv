"""
Automated Windows Builder for Universal Media Converter.
Executes on Windows to install requirements, download FFmpeg, and build standalone EXE.
"""

import os
import sys
import shutil
import zipfile
import urllib.request
import subprocess
from typing import Optional, List, Dict

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RESOURCES_DIR = os.path.join(ROOT_DIR, "1_resources")
FINAL_DIR = os.path.join(ROOT_DIR, "4_final")
DIST_WIN_DIR = os.path.join(FINAL_DIR, "dist_windows")
WORK_WIN_DIR = os.path.join(FINAL_DIR, "build_windows")
SPEC_FILE = os.path.join(RESOURCES_DIR, "UniversalMediaConverter_windows.spec")
REQUIREMENTS_FILE = os.path.join(RESOURCES_DIR, "requirements.txt")


def log(msg: str):
    print(f"\n>>> {msg}\n")


def check_python_version():
    log(f"Verwende Python: {sys.executable} (Version {sys.version.split()[0]})")
    if sys.version_info < (3, 9):
        print("[WARNUNG] Python 3.9 oder neuer wird empfohlen.")


def install_dependencies():
    log("[1/3] Installiere / Aktualisiere PyInstaller und Abhaengigkeiten...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller", "-r", REQUIREMENTS_FILE])


def ensure_windows_ffmpeg():
    log("[2/3] Ueberpruefe FFmpeg fuer Windows...")
    ffmpeg_exe = os.path.join(RESOURCES_DIR, "ffmpeg.exe")
    ffprobe_exe = os.path.join(RESOURCES_DIR, "ffprobe.exe")

    if os.path.isfile(ffmpeg_exe) and os.path.isfile(ffprobe_exe):
        log("FFmpeg und FFprobe sind bereits in 1_resources vorhanden.")
        return

    # Check system PATH first
    sys_ffmpeg = shutil.which("ffmpeg.exe") or shutil.which("ffmpeg")
    sys_ffprobe = shutil.which("ffprobe.exe") or shutil.which("ffprobe")
    if sys_ffmpeg and sys_ffprobe:
        log(f"FFmpeg im System-PATH gefunden: {sys_ffmpeg}")
        shutil.copy2(sys_ffmpeg, ffmpeg_exe)
        shutil.copy2(sys_ffprobe, ffprobe_exe)
        return

    # Download prebuilt static Windows FFmpeg from BtbN
    url = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
    zip_path = os.path.join(RESOURCES_DIR, "ffmpeg_download.zip")
    log(f"Lade FFmpeg fuer Windows herunter von:\n{url}")

    def progress_hook(block_num, block_size, total_size):
        downloaded = block_num * block_size
        if total_size > 0:
            percent = min(100.0, downloaded * 100.0 / total_size)
            sys.stdout.write(f"\rDownload: {downloaded / (1024*1024):.1f} MB / {total_size / (1024*1024):.1f} MB ({percent:.1f}%)")
            sys.stdout.flush()

    try:
        urllib.request.urlretrieve(url, zip_path, reporthook=progress_hook)
        print("\nDownload abgeschlossen. Entpacke FFmpeg...")

        with zipfile.ZipFile(zip_path, "r") as z:
            for member in z.namelist():
                base_name = os.path.basename(member).lower()
                if base_name in ("ffmpeg.exe", "ffprobe.exe"):
                    target_file = os.path.join(RESOURCES_DIR, base_name)
                    with z.open(member) as src, open(target_file, "wb") as dst:
                        shutil.copyfileobj(src, dst)
                    print(f"Entpackt: {target_file}")

        if os.path.exists(zip_path):
            os.remove(zip_path)

        if not (os.path.isfile(ffmpeg_exe) and os.path.isfile(ffprobe_exe)):
            raise RuntimeError("ffmpeg.exe oder ffprobe.exe konnten nicht im ZIP-Archiv gefunden werden.")

        log("FFmpeg erfolgreich eingerichtet.")
    except Exception as e:
        print(f"[WARNUNG] Automatischer FFmpeg-Download fehlgeschlagen: {e}")
        print("Hinweis: Die App wird trotzdem gebaut. FFmpeg kann nachtraeglich in den App-Ordner gelegt werden.")


def build_pyinstaller():
    log("[3/3] Kompiliere Windows EXE mit PyInstaller...")
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--distpath",
        DIST_WIN_DIR,
        "--workpath",
        WORK_WIN_DIR,
        SPEC_FILE,
    ]
    subprocess.check_call(cmd)

    output_exe = os.path.join(DIST_WIN_DIR, "UniversalMediaConverter", "UniversalMediaConverter.exe")
    if os.path.isfile(output_exe):
        print("\n" + "=" * 65)
        print("  ERFOLG! Die Windows EXE wurde erfolgreich erstellt:")
        print(f"  {output_exe}")
        print("=" * 65 + "\n")
    else:
        print(f"[WARNUNG] Build abgeschlossen, aber EXE nicht am erwarteten Pfad gefunden: {output_exe}")


def find_or_install_inno_setup() -> Optional[str]:
    candidates = [
        shutil.which("iscc"),
        shutil.which("iscc.exe"),
        r"C:\Program Files (x86)\Inno Setup 6\iscc.exe",
        r"C:\Program Files\Inno Setup 6\iscc.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Inno Setup 6\iscc.exe"),
    ]
    for c in candidates:
        if c and os.path.isfile(c):
            return c

    log("Inno Setup Compiler (ISCC) wird gesucht oder installiert...")

    # Attempt 1: winget
    winget = shutil.which("winget")
    if winget:
        try:
            print("Installiere Inno Setup via winget...")
            subprocess.run(
                ["winget", "install", "--id", "JR.InnoSetup", "-e", "--silent", "--accept-source-agreements", "--accept-package-agreements"],
                check=False
            )
            for c in candidates[2:]:
                if os.path.isfile(c):
                    return c
        except Exception:
            pass

    # Attempt 2: download official Inno Setup installer and run silent setup
    inno_url = "https://files.jrsoftware.org/is/6/innosetup-6.3.3.exe"
    tmp_installer = os.path.join(RESOURCES_DIR, "inno_setup_installer.exe")
    try:
        print(f"Lade Inno Setup herunter: {inno_url}")
        urllib.request.urlretrieve(inno_url, tmp_installer)
        print("Installiere Inno Setup automatisch...")
        subprocess.run([tmp_installer, "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/SP-"], check=True)
        if os.path.exists(tmp_installer):
            os.remove(tmp_installer)
        for c in candidates[2:]:
            if os.path.isfile(c):
                return c
    except Exception as e:
        print(f"[WARNUNG] Automatisches Installieren von Inno Setup fehlgeschlagen: {e}")

    return None


def create_installer():
    log("[4/4] Erstelle Windows Setup.exe Installer mit Inno Setup...")
    iss_file = os.path.join(RESOURCES_DIR, "installer.iss")
    if not os.path.isfile(iss_file):
        print(f"[FEHLER] Inno Setup Skript nicht gefunden: {iss_file}")
        return

    iscc = find_or_install_inno_setup()
    if not iscc:
        print("\n" + "=" * 65)
        print("  HINWEIS ZUR SETUP.EXE:")
        print("  Inno Setup Compiler wurde nicht gefunden.")
        print("  Falls die automatische Installation nicht geklappt hat:")
        print("  1. Lade Inno Setup herunter: https://jrsoftware.org/isdl.php")
        print("  2. Nach der Installation Rechtsklick auf '1_resources\\installer.iss'")
        print("     und 'Compile' auswaehlen.")
        print("=" * 65 + "\n")
        return

    print(f"Kompiliere Installer mit: {iscc}")
    subprocess.check_call([iscc, iss_file])

    setup_exe = os.path.join(FINAL_DIR, "UniversalMediaConverter_Setup.exe")
    if os.path.isfile(setup_exe):
        print("\n" + "=" * 65)
        print("  ERFOLG! Der Setup-Installer wurde erstellt:")
        print(f"  {setup_exe}")
        print("=" * 65 + "\n")
    else:
        print(f"[WARNUNG] Setup.exe wurde nicht am erwarteten Pfad gefunden: {setup_exe}")


def main():
    print("=" * 65)
    print("  Universal Media Converter - Windows Build Prozess")
    print("=" * 65)
    check_python_version()
    install_dependencies()
    ensure_windows_ffmpeg()
    build_pyinstaller()
    create_installer()


if __name__ == "__main__":
    try:
        main()
    except Exception as err:
        print(f"\n[FEHLER WAEHREND DES BUILDS]: {err}")
        sys.exit(1)
