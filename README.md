# Universal Media, Image & Document Converter (macOS)

Ein moderner, lokaler All-in-One Converter für macOS mit ausblendbarer Seitenleiste, Drag-and-Drop, YouTube-Downloader, Bild- und Dokumentenkonvertierung.

---

## Die 4 Bereiche (Navigation über linke Seitenleiste)

Über den Button "Menü einblenden / ausblenden" oben links lässt sich die linke Navigationsleiste jederzeit ein- und ausblenden.

### 1. YouTube Downloader
- Formate: MP3, MP4, WAV, FLAC, M4A, MOV
- Qualität: Bis zu 320 kbps (High Quality Audio) bzw. bis zu 4K / 1080p Full HD Video
- Cover & Tags: Album-Cover und ID3-Tags (Künstler, Titel, Jahr) werden automatisch eingebettet
- Batch-Download: Beliebig viele Links auf einmal in die Warteschlange einfügen

### 2. Audio & Video Konverter
- Video zu Audio: MP4, MOV, MKV, AVI, WEBM in MP3, WAV, FLAC, AIFF, AAC, OGG, OPUS
- Audio zu Audio: MP3 in WAV, FLAC, AIFF (unkomprimierte Studioqualität), AAC, OGG, OPUS
- Video zu Video: MP4 in MOV (QuickTime), MKV, WEBM, AVI oder animiertes GIF
- Skalierung & Bitrate: Bis zu 320 kbps bzw. Auflösung 1080p, 720p, 480p

### 3. Bilder-Konverter (High Quality)
- Unterstützte Eingabeformate: JPEG, JPG, HEIC, PNG, WEBP, TIFF, BMP, GIF, ICO, PSD, AVIF
- Zielformate:
  - JPEG / JPG: Wählbare Qualitätsstufen (Maximum 100%, 95%, 85%, 75%)
  - PNG: Verlustfrei mit Alphakanal/Transparenz
  - HEIC: Apple High-Efficiency Format
  - WebP: Modernes Web-Format (Lossless oder komprimiert)
  - TIFF / BMP: Unkomprimierte Druck- und Archivierungsqualität
  - ICO: Erzeugt Multi-Size Icons (16x16 bis 256x256) für Websites und Apps
  - PDF: Wandelt Bilder direkt in ein PDF-Dokument um

### 4. Dokumente & Tabellen
- PDF in DOCX: Wandelt PDF-Dateien in formatierte, editierbare Microsoft Word Dokumente um
- PDF in TXT / PNG: Text-Extraktion oder Seiten als hochauflösende Bilder rendern
- XLSX in CSV / PDF / JSON / HTML: Excel-Tabellen in CSV, formatierte PDF-Tabellen oder JSON exportieren
- CSV in XLSX / PDF / JSON / HTML: CSV-Dateien in echte Excel-Mappen oder PDF-Tabellen konvertieren
- DOCX in PDF / TXT / HTML / RTF: Word-Dokumente in PDF oder Text exportieren
- TXT in DOCX / PDF: Reine Textdateien in Word-Dokumente oder PDF-Dateien überführen

---

## Standard-Speicherort

Der Speicherort passt sich **dynamisch dem jeweiligen macOS-Benutzer** an:
* Auf deinem Mac: `/Users/elias/Downloads`
* Auf Max' Mac: `/Users/max/Downloads`
* Auf jedem Mac: `/Users/<Benutzer>/Downloads`
* Kann in der Leiste jederzeit per Klick auf „Ordner wählen…“ geändert werden.

---

## App testen (macOS)

Starte die App einfach aus diesem Ordner:
* **Per Doppelklick im Finder:** [`4_final/start_converter.command`](file:///Users/elias/Elias/Converter/4_final/start_converter.command)
* **Über das Terminal:** `./4_final/start.sh`

---

## macOS Installation & DMG

Die fertige Standalone-Installationsdatei für macOS liegt bereit unter:
* [`4_final/UniversalMediaConverter.dmg`](file:///Users/elias/Elias/Converter/4_final/UniversalMediaConverter.dmg)

Einfach die `.dmg`-Datei per Doppelklick öffnen und **Universal Media Converter** in den Programme-Ordner (`/Applications`) ziehen. Die App läuft eigenständig auf jedem Apple Silicon Mac (M1/M2/M3/M4) ohne zusätzliche Software-Installationen.

Zum erneuten Erstellen des DMG-Installers:
```bash
./4_final/build_dmg.sh
```

---

## Windows Version (.exe)

Da Python-Anwendungen mit nativen C/C++-Bibliotheken (wie PyQt6, PyMuPDF, Pillow und FFmpeg) Windows-spezifische DLLs und Windows PE-Dateien benötigen, kann PyInstaller nicht direkt von macOS nach Windows cross-kompilieren.

Der gesamte Code und alle Build-Dateien wurden jedoch vollständig für Windows vorbereitet und getestet:

### Option 1: Auf einem Windows-PC oder Windows-VM (Parallels / UTM / VirtualBox)
1. Kopiere den Projektordner auf einen Windows-Rechner.
2. Führe per Doppelklick die Datei aus:
   > [`4_final/build_exe.bat`](file:///Users/elias/Elias/Converter/4_final/build_exe.bat)
3. Das Skript richtet automatisch die Umgebung ein, lädt Windows-FFmpeg herunter, kompiliert die Anwendung und erzeugt automatisch mit Inno Setup den fertigen Setup-Installer:
   > `4_final\UniversalMediaConverter_Setup.exe`
4. Diese einzelne `Setup.exe` kannst du an jeden verschicken!

### Option 2: Kostenlos in der Cloud über GitHub Actions (ohne Windows-PC)
1. Das Projekt enthält bereits einen fertigen Workflow in [`.github/workflows/build_windows.yml`](file:///Users/elias/Elias/Converter/.github/workflows/build_windows.yml).
2. Lade den Ordner in ein GitHub-Repository hoch.
3. GitHub startet automatisch einen Windows-Server (`windows-latest`), kompiliert die `.exe`, erstellt die `Setup.exe` mit Inno Setup und stellt die fertige `UniversalMediaConverter_Setup.exe` unter **Actions ➔ Artifacts** zum Download bereit.

---

## Android Version (.apk für Samsung Galaxy A55 5G)

Die App wurde speziell für das **Samsung Galaxy A55 5G (ARM64 / Exynos 1480, Android 14/15/16)** optimiert:
* **App-Ordner:** [`android_app/`](file:///Users/elias/Elias/Converter/android_app/)
* **Mobile Touch-Oberfläche:** Kivy Touch-UI mit Dark Theme, YouTube-Downloader (MP3/MP4/M4A/WAV), direktem Einfügen aus der Android-Zwischenablage und Speicher-Integration in `Download/UniversalConverter` (sichtbar in Samsung *Eigene Dateien* & Galerie).
* **Konfiguration:** [`android_app/buildozer.spec`](file:///Users/elias/Elias/Converter/android_app/buildozer.spec)
* **Cloud-Build-Workflow:** [`.github/workflows/build_android_apk.yml`](file:///Users/elias/Elias/Converter/.github/workflows/build_android_apk.yml)

### APK automatisch erstellen & auf dem Galaxy A55 installieren:
1. Lade das Projekt in dein GitHub-Repository hoch.
2. Gehe auf **Actions** ➔ **Build Android APK (Galaxy A55 5G)**.
3. Nach dem Build kannst du unter **Artifacts** die Datei `UniversalMediaConverter-GalaxyA55.apk` direkt auf dein Samsung-Handy herunterladen.
4. Tippe die `.apk` auf deinem Samsung-Handy an und wähle **„Installieren“** (falls gefragt, die Berechtigung *„Aus dieser Quelle installieren“* kurz in den Einstellungen aktivieren).


