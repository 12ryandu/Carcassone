# env/tile.py

from dataclasses import dataclass, field
from typing import List

from env.meeple import Meeple

EdgeList = List[int]

@dataclass
class Feature:
    type: str  # e.g., "CityFeature", "FieldFeature"
    connectedEdges: EdgeList
    meeples: list[Meeple] = field(default_factory=list)
    id: int = -1


@dataclass
class CityFeature(Feature):
    hasShield: bool = False
    hasDouble: bool = False

    def __init__(self, connected_edges: EdgeList, has_shield: bool = False, has_double: bool = False):
        super().__init__("CityFeature", connected_edges)
        self.hasShield = has_shield
        self.hasDouble = has_double

@dataclass
class RoadFeature(Feature):
    hasInn: bool = False


    def __init__(self, connected_edges: EdgeList, has_inn: bool = False):
        super().__init__("RoadFeature", connected_edges)
        self.hasInn = has_inn

@dataclass
class FieldFeature(Feature):

    def __init__(self, connected_edges: EdgeList):
        super().__init__("FieldFeature", connected_edges)

@dataclass
class CloisterFeature(Feature):
    def __init__(self):
        super().__init__("CloisterFeature", [])

@dataclass
class GardenFeature(Feature):
    def __init__(self):
        super().__init__("GardenFeature", [])

@dataclass
class Tile:
    id: str
    rotation: int
    features: List[Feature]

    def __init__(self, id, features, rotation=0):
        self.id = id
        self.features = features
        self.rotation = rotation

    def get_feature_except_road(self) -> list[Feature]:

        fers = []
        for feature in self.features:
            if feature.type != "RoadFeature":
                fers.append(feature)
        return fers
    def get_feature_of_road(self) -> list[Feature]:

        fors = []
        for feature in self.features:
            if feature.type == "RoadFeature":
                fors.append(feature)

        return fors

    @staticmethod
    def from_dict(data: dict) -> "Tile":
        features = []
        for f in data["features"]:
            name = f["name"]
            if name == "CityFeature":
                features.append(CityFeature(
                    connected_edges=f["connectedEdges"],
                    has_shield=f.get("hasShield", False),
                    has_double=f.get("hasDouble", False)
                ))
            elif name == "RoadFeature":
                features.append(RoadFeature(
                    connected_edges=f["connectedEdges"],
                    has_inn=f.get("hasInn", False)
                ))
            elif name == "FieldFeature":
                features.append(FieldFeature(f["connectedEdges"]))
            elif name == "CloisterFeature":
                features.append(CloisterFeature())
            elif name == "GardenFeature":
                features.append(GardenFeature())
        return Tile(id=str(data["id"]),
                    rotation=data.get("rotation", 0),
                    features=features)

    def get_feature_by_edge(self, edge1: int) -> str:
        rotate = self.rotation

        # 处理道路部分
        fors = self.get_feature_of_road()
        edge_of_road = (edge1 // 2 - rotate) % 4
        for f in fors:
            if edge_of_road in f.connectedEdges:
                return "RoadFeature"

        # 处理非道路特征
        fers = self.get_feature_except_road()
        rotated_edge = (edge1 - 2 * rotate) % 8
        for f in fers:
            if rotated_edge in f.connectedEdges:
                return f.type
        return ""

    def get_meeple(self):
        result = []
        for feature in self.features:
            if len(feature.meeples) > 0:
                result.append(feature)
        return result

    def get_meeple_proper_position(self, feature: Feature, rotate: int):
        edge_mapping_coord = {
            0: (25, 0),  # 上左
            1: (75, 0),  # 上右
            2: (100, 25),  # 右上
            3: (100, 75),  # 右下
            4: (75, 100),  # 下右
            5: (25, 100),  # 下左
            6: (0, 75),  # 左下
            7: (0, 25)  # 左上
        }

        edge_mapping_coord_for_road = {
            0: (50, 10),
            1: (90, 50),
            2: (50, 90),
            3: (10, 50)
        }

        if feature.type == "RoadFeature":
            edge = feature.connectedEdges[0]
            rotated_edge = (edge - rotate) % 4
            return edge_mapping_coord_for_road[rotated_edge]

        elif feature.type in ["CloisterFeature", "GardenFeature"]:
            return (50, 50)

        elif feature.type in ["FieldFeature", "CityFeature"]:
            total_x = 0
            total_y = 0
            count = 0
            for edge in feature.connectedEdges:
                rotated_edge = (edge - 2 * rotate) % 8
                if rotated_edge in edge_mapping_coord:
                    x, y = edge_mapping_coord[rotated_edge]
                    total_x += x
                    total_y += y
                    count += 1

            if count == 0:
                return (50, 50)
            return (total_x // count, total_y // count)















