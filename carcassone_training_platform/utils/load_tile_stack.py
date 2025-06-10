# utils/load_tiles.py

import json
from typing import List
from env.tile import Tile

def load_tile_stack(filepath: str) -> List[Tile]:
    with open(filepath, "r") as f:
        data = json.load(f)

        return [Tile.from_dict(tile_dict) for tile_dict in data]
