from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass
class Meeple:
    id: int
    owner: str                     # 玩家名
    type: str                      # "normal", "pig", etc.         # "RoadFeature" / "CityFeature" / "FieldFeature"
    feature_id: int
    active: bool = False
    frontend_coord : tuple[int,int] = None

MEEPLE_EXCLUSIVE = [
    "normal",
    "big",

]