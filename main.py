import plistlib
import re

from PIL import Image
from gd_icon_composite import Icon22, IconBuilder22, COLOR_WHITE
import os

from export_icon_22 import export_icon22

SEARCH_DIR = os.getcwd()
EXPORT_DIR = os.path.join(SEARCH_DIR, "medium")

def filter_sprite_sheets(item: os.DirEntry):
    if re.search(r".*_\d*-uhd\.plist", item.name):
        return True
    return False

print("Searching for uhd plists...")

builder = IconBuilder22(COLOR_WHITE, COLOR_WHITE, COLOR_WHITE, True, SEARCH_DIR)
found_icons = list()
with os.scandir(SEARCH_DIR) as working_dir:
    for entry in filter(filter_sprite_sheets, working_dir):
        with open(entry, "rb") as plist_file:
            plist = plistlib.load(plist_file)
        try:
            source_spritesheet = Image.open(f"{entry.name.rsplit('.', 1)[0]}.png").convert("RGBA")
            found_icons.append(Icon22.from_spritesheet(source_spritesheet, plist, builder.color_config))
        except ValueError as error:
            print(f"\tskipping {entry.name.rsplit('.', 1)[0]}: "
                  f"{error}")
        except FileNotFoundError:
            print(f"\tskipping {entry.name.rsplit('.', 1)[0]}: "
                  f"no sprite sheet file ({entry.name.rsplit('.', 1)[0]}.png) found")

print(f"Found {len(found_icons)} valid icons")
print(f"Exporting found icons to \"hd\" in {EXPORT_DIR}")

if not os.path.exists(EXPORT_DIR):
    os.mkdir(EXPORT_DIR)

def tab_print(*string):
    print(f"\t\t{' '.join(str(s) for s in string)}")

for icon in found_icons:
    print(f"\tExporting {icon.gamemode_name}_{icon.id}:")
    export_icon22(icon, EXPORT_DIR, tab_print, target_quality="-hd")

print(f"Export complete")