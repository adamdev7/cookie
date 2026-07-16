"""Crop the 3x2 menu showcase into six flavor images."""
from pathlib import Path

from PIL import Image

BASE = Path(__file__).resolve().parent.parent
SOURCE = BASE / "static" / "images" / "menu-showcase.png"
OUT_DIR = BASE / "static" / "images" / "flavors"

# (col, row) -> filename
FLAVOR_GRID = [
    ((0, 0), "oreo.png"),
    ((1, 0), "red-velvet.png"),
    ((2, 0), "lotus.png"),
    ((0, 1), "confetti.png"),
    ((1, 1), "chocolat-chips.png"),
    ((2, 1), "mms.png"),
]


def main():
    if not SOURCE.exists():
        alt = Path(
            r"C:\Users\adaml\.cursor\projects\c-Users-adaml-OneDrive-D4TECH-Cookies\assets"
            r"\c__Users_adaml_AppData_Roaming_Cursor_User_workspaceStorage_152706f686d94e9087b171ecc0789fc4_images_IMG_0318-4326be30-d6c2-4a58-8394-2bcbca9cf187.png"
        )
        if alt.exists():
            import shutil

            shutil.copy(alt, SOURCE)
        else:
            raise FileNotFoundError(f"Source image not found: {SOURCE}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    img = Image.open(SOURCE)
    w, h = img.size
    cols, rows = 3, 2
    cell_w, cell_h = w // cols, h // rows
    pad = int(min(cell_w, cell_h) * 0.04)

    for (col, row), name in FLAVOR_GRID:
        left = col * cell_w + pad
        top = row * cell_h + pad
        right = (col + 1) * cell_w - pad
        bottom = (row + 1) * cell_h - pad
        crop = img.crop((left, top, right, bottom))
        crop.save(OUT_DIR / name, quality=92)
        print(f"Saved {name} ({crop.size[0]}x{crop.size[1]})")


if __name__ == "__main__":
    main()
