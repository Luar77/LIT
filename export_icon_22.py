import copy
import json
import math
import os
import plistlib
import shutil
from typing import Callable

from PIL import Image
from PyTexturePacker import Packer, Utils
from gd_icon_composite import Icon22


def export_icon22(icon: Icon22, result_dir: str, log_func: Callable = print,
                  target_quality: str = "-uhd", resampling: Image.Resampling = Image.Resampling.HAMMING):

    formal_icon_name = f"{icon.gamemode_name}_{icon.id:0>2}{target_quality}"
    icon_name_dir = os.path.join(result_dir, formal_icon_name)

    if not os.path.exists(icon_name_dir):
        os.mkdir(os.path.join(result_dir, formal_icon_name))

    offsets = copy.deepcopy(icon.offsets)

    log_func("generating spritesheet")

    def image_reduce_with_offset(image: Image.Image, factor: int):
        big_size = (int(math.ceil(image.width / factor)), int(math.ceil(image.height / factor)))
        image = image.resize(big_size, resample=resampling)
        return image

    img_quality_transform = {
        "-uhd": lambda img: img,
        "-hd": lambda img: image_reduce_with_offset(img, 2),
        "": lambda img: image_reduce_with_offset(img, 4)
    }

    part_source_sizes = dict()

    # gets every sprite of this icon, and saves them to results/icon_name (this is a temporary folder)
    for part, images in icon.images.items():
        s_size = [0, 0, 0, 0]
        for layer_name, sprite in images.items():

            log_func(f"{part}_{layer_name}.png", sprite.size)
            # reduces icon quality to target quality (assuming base quality is uhd)
            sprite = img_quality_transform.get(target_quality, img_quality_transform["-uhd"])(sprite)

            if sprite.size == (0, 0):
                sprite = Image.new("RGBA", (1, 1), (0, 0, 0, 0))

            # figure out the spriteSourceSize for the entire part
            sprite_pos = (- sprite.width + offsets[part][layer_name][0],
                          - sprite.height + offsets[part][layer_name][1],
                          sprite.width + offsets[part][layer_name][0],
                          sprite.height + offsets[part][layer_name][1])
            s_size[0] = s_size[0] if s_size[0] < sprite_pos[0] else sprite_pos[0]
            s_size[1] = s_size[1] if s_size[1] < sprite_pos[1] else sprite_pos[1]
            s_size[2] = s_size[2] if s_size[2] > sprite_pos[2] else sprite_pos[2]
            s_size[3] = s_size[3] if s_size[3] > sprite_pos[3] else sprite_pos[3]

            sprite.save(os.path.join(icon_name_dir, f"{part}_{layer_name}.png"))
        part_source_sizes[part] = (round((abs(s_size[0]) + s_size[2]) / 2),
                                   round((abs(s_size[1]) + s_size[3]) / 2))

    packer = Packer.create(atlas_format=Utils.ATLAS_FORMAT_JSON)
    packer.pack(icon_name_dir, formal_icon_name, icon_name_dir)

    log_func("generating plist")

    icon_spritesheet = Image.open(os.path.join(icon_name_dir, f"{formal_icon_name}.png"))

    plist_dict = {
        "frames": {},
        "metadata": {
            "format": 3,
            "pixelFormat": "RGBA4444",
            "premultiplyAlpha": False,
            "realTextureFileName": f"icons/{formal_icon_name}.png",
            "size": f"{{{icon_spritesheet.width},{icon_spritesheet.height}}}",
            "smartupdate": "",
            "textureFileName": f"icons/{formal_icon_name}.png"
        }
    }

    icon_spritesheet.save(os.path.join(result_dir, f"{formal_icon_name}.png"))
    icon_spritesheet.close()

    with open(os.path.join(icon_name_dir, f"{formal_icon_name}.json")) as json_file:
        json_data = json.load(json_file)

    # ("p1", ""), ("p2", "_2"), ("extra", "_extra"), ("dome", "_3"))

    formal_layer_names = {
        "p1": "",
        "p2": "_2",
        "extra": "_extra",
        "dome": "_3",
        "glow": "_glow"
    }

    include_part_name = icon.gamemode_name in {"robot", "spider"}

    offset_quality_map = {
        "-uhd": lambda x: str(x),
        "-hd": lambda x: f"{x / 2:.4f}".rstrip('0').rstrip('.') if x / 2 != int(x / 2) else str(int(x / 2)),
        "": lambda x: f"{x / 4:.5f}".rstrip('0').rstrip('.') if x / 4 != int(x / 4) else str(int(x / 4)),
        # "-hd": lambda x: f"{x / 2:.1f}",
        # "": lambda x: f"{x / 4:.1f}",
    }

    for sprite_name, sprite_data in json_data["frames"].items():

        sprite_name = sprite_name.rstrip(".png")
        part_name, layer_name = sprite_name.split("_")
        log_func(sprite_name)

        sprite_name = f"{icon.gamemode_name}_{icon.id:0>2}" \
                      f"{f'_{part_name}' if include_part_name else ''}{formal_layer_names[layer_name]}_001.png"

        sprite_offset_string = ",".join(tuple(map(offset_quality_map[target_quality],
                                                    offsets[part_name][layer_name])))

        new_sprite_data = {
            "aliases": [],
            "spriteOffset": f'{{{sprite_offset_string}}}',
            "spriteSize": f"{{{sprite_data['spriteSourceSize']['w']},"
                          f"{sprite_data['spriteSourceSize']['h']}}}",
            "spriteSourceSize": f"{{{part_source_sizes[part_name][0]},"
                                f"{part_source_sizes[part_name][1]}}}",
            "textureRect": f"{{{{{sprite_data['frame']['x']},"
                           f"{sprite_data['frame']['y']}}},"
                           f"{{{sprite_data['frame']['w']},"
                           f"{sprite_data['frame']['h']}}}}}",
            "textureRotated": sprite_data["rotated"]
        }
        plist_dict["frames"][sprite_name] = new_sprite_data

    with open(os.path.join(result_dir, f"{formal_icon_name}.plist"), "wb") as p_file:
        plistlib.dump(plist_dict, p_file)

    shutil.rmtree(os.path.join(result_dir, formal_icon_name))