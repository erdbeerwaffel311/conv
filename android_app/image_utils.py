"""Image conversion utility supporting JPEG, HEIC, PNG, WEBP, TIFF, BMP, GIF, ICO, PDF."""

import os
import sys
import subprocess
from typing import Callable, Dict, Optional, Tuple, List
from PIL import Image
import pillow_heif

# Register HEIF opener so PIL natively handles HEIC/HEIF files
pillow_heif.register_heif_opener()


IMAGE_FORMATS = {
    "JPEG": {
        "ext": "jpg",
        "description": "JPEG / JPG - Hohe Kompatibilität",
        "qualities": ["Maximum (100%)", "Sehr hoch (95%)", "Hoch (85%)", "Mittel (75%)"],
        "default_quality": "Sehr hoch (95%)",
    },
    "PNG": {
        "ext": "png",
        "description": "PNG - Verlustfrei mit Transparenz",
        "qualities": ["Lossless (Verlustfrei)"],
        "default_quality": "Lossless (Verlustfrei)",
    },
    "HEIC": {
        "ext": "heic",
        "description": "HEIC - Apple High Efficiency Format",
        "qualities": ["Maximum (100%)", "Sehr hoch (95%)", "Hoch (85%)"],
        "default_quality": "Sehr hoch (95%)",
    },
    "WEBP": {
        "ext": "webp",
        "description": "WebP - Modernes hocheffizientes Web-Format",
        "qualities": ["Lossless (Verlustfrei)", "Sehr hoch (95%)", "Hoch (85%)"],
        "default_quality": "Sehr hoch (95%)",
    },
    "TIFF": {
        "ext": "tiff",
        "description": "TIFF - Druck- und Archivierungsqualität",
        "qualities": ["Lossless (Verlustfrei)"],
        "default_quality": "Lossless (Verlustfrei)",
    },
    "BMP": {
        "ext": "bmp",
        "description": "BMP - Unkomprimierte Bitmap",
        "qualities": ["Lossless (Verlustfrei)"],
        "default_quality": "Lossless (Verlustfrei)",
    },
    "GIF": {
        "ext": "gif",
        "description": "GIF - Standard Grafikformat",
        "qualities": ["Standard"],
        "default_quality": "Standard",
    },
    "ICO": {
        "ext": "ico",
        "description": "ICO - Windows / Favicon Icon",
        "qualities": ["Multi-Size (16, 32, 48, 64, 128, 256)"],
        "default_quality": "Multi-Size",
    },
    "PDF": {
        "ext": "pdf",
        "description": "PDF - Bild als Dokument speichern",
        "qualities": ["Standard"],
        "default_quality": "Standard",
    },
}


def convert_image(
    input_file: str,
    output_file: str,
    target_format: str,
    quality_str: str = "Sehr hoch (95%)",
    progress_callback: Optional[Callable[[float, str], None]] = None,
) -> Tuple[bool, str]:
    """Converts an image file to the target format with specified quality."""
    if not os.path.isfile(input_file):
        return False, f"Eingabedatei existiert nicht: {input_file}"

    target_fmt = target_format.upper()
    out_dir = os.path.dirname(output_file)
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)

    if progress_callback:
        progress_callback(15.0, "Lese Bild...")

    # Parse numeric quality
    q_val = 95
    if "100%" in quality_str:
        q_val = 100
    elif "95%" in quality_str:
        q_val = 95
    elif "85%" in quality_str:
        q_val = 85
    elif "75%" in quality_str:
        q_val = 75

    try:
        # Native macOS sips fallback for HEIC if needed, but Pillow with pillow_heif handles it
        with Image.open(input_file) as im:
            if progress_callback:
                progress_callback(40.0, "Verarbeite Farbräume...")

            # Handle format specifics
            if target_fmt in ["JPEG", "JPG"]:
                if im.mode in ("RGBA", "LA", "P"):
                    # Convert transparent background to white
                    bg = Image.new("RGB", im.size, (255, 255, 255))
                    if im.mode == "P":
                        im = im.convert("RGBA")
                    bg.paste(im, mask=im.split()[-1] if len(im.split()) > 3 else None)
                    im = bg
                elif im.mode != "RGB":
                    im = im.convert("RGB")
                im.save(output_file, "JPEG", quality=q_val, optimize=True)

            elif target_fmt == "PNG":
                im.save(output_file, "PNG", optimize=True)

            elif target_fmt == "HEIC":
                # Convert using pillow_heif or sips
                if im.mode not in ("RGB", "RGBA"):
                    im = im.convert("RGB")
                try:
                    # Save with pillow_heif
                    heif_file = pillow_heif.from_pillow(im)
                    heif_file.save(output_file, quality=q_val)
                except Exception as e:
                    # Fallback to macOS native sips if on macOS
                    if sys.platform == "darwin":
                        tmp_png = output_file + ".tmp.png"
                        im.save(tmp_png, "PNG")
                        subprocess.run(["sips", "-s", "format", "heic", tmp_png, "--out", output_file], check=True)
                        if os.path.exists(tmp_png):
                            os.remove(tmp_png)
                    else:
                        raise RuntimeError(f"HEIC konnte nicht gespeichert werden: {str(e)}")

            elif target_fmt == "WEBP":
                lossless = "Lossless" in quality_str
                im.save(output_file, "WEBP", quality=q_val, lossless=lossless)

            elif target_fmt == "TIFF":
                im.save(output_file, "TIFF", compression="tiff_lzw")

            elif target_fmt == "BMP":
                if im.mode not in ("RGB", "L"):
                    im = im.convert("RGB")
                im.save(output_file, "BMP")

            elif target_fmt == "GIF":
                im.save(output_file, "GIF")

            elif target_fmt == "ICO":
                if im.mode != "RGBA":
                    im = im.convert("RGBA")
                icon_sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
                im.save(output_file, format="ICO", sizes=icon_sizes)

            elif target_fmt == "PDF":
                if im.mode not in ("RGB", "L"):
                    im = im.convert("RGB")
                im.save(output_file, "PDF", resolution=100.0)

            else:
                im.save(output_file)

        if progress_callback:
            progress_callback(100.0, "Fertig!")
        return True, "Bild erfolgreich konvertiert"

    except Exception as e:
        return False, f"Fehler bei Bildkonvertierung: {str(e)}"
