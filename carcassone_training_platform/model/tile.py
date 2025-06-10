from typing import List, Literal, Union
from dataclasses import dataclass

EdgeList = List[int]

@dataclass
class Feature:
    type: Literal["FieldFeature", "RoadFeature", "CityFeature"]
    connectedEdges: EdgeList

@dataclass
class FieldFeature(Feature):
    def __init__(self, connectedEdges: EdgeList):
        super().__init__("FieldFeature", connectedEdges)

@dataclass
class RoadFeature(Feature):
    hasInn: bool

    def __init__(self, connectedEdges: EdgeList, hasInn: bool):
        super().__init__("RoadFeature", connectedEdges)
        self.hasInn = hasInn

@dataclass
class CityFeature(Feature):
    hasShield: bool
    hasDouble: bool

    def __init__(self, connectedEdges: EdgeList, hasShield: bool, hasDouble: bool):
        super().__init__("CityFeature", connectedEdges)
        self.hasShield = hasShield
        self.hasDouble = hasDouble

@dataclass
class GardenFeature(Feature):

    def __init__(self, connectedEdges: EdgeList = []):
        super().__init__("GardenFeature", connectedEdges)

@dataclass
class Tile:
    id: str
    image: str
    features: List[Feature]
