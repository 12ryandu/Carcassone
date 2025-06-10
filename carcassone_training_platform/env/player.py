from dataclasses import dataclass, field
from typing import List, Optional

from env.meeple import Meeple


@dataclass
class Player:
    player_id: int
    name: str                         # 玩家名（唯一标识）
    color: str                        # 玩家颜色（用于前端区分）
    score: int = 0                    # 当前得分
    meeples: List[Meeple] = field(default_factory=list)  # 手中未放置的 meeple


    def __init__(self, name: str, color: str,):
        self.player_id = int(name[-1])
        self.name = name
        self.color = color
        self.score = 0
        self.meeples = [
            Meeple(id=i, owner=name, type="normal", feature_id=-1, active=False)
            for i in range(7)
        ]

    def get_available_meeples(self, meeple_type: str) -> List[Meeple]:
        """返回未使用的某类型 meeple 列表"""
        return [m for m in self.meeples if m.type == meeple_type and m.active == False]

    def place_meeple(self, meeple: Meeple):
        """放置一个 meeple（将其激活）"""
        for m in self.meeples:
            if m.id == meeple.id:
                m.active = True
                break

    def place_meeple_by_type(self, meeple_type: str):

        for m in self.meeples:
            if m.type == meeple_type and not m.active:
                m.active = True
                return m


    def get_available_meeple_by_type(self, meeple_type: str) -> Optional[Meeple]:
        """
        返回一个未激活的指定类型的 meeple，如果没有则返回 None。
        """
        for meeple in self.meeples:
            if meeple.type == meeple_type and not meeple.active:
                return meeple
        return None


    def return_meeple(self, meeple_id: int):
        """回收一个 meeple（打分后返回手中）"""
        for m in self.meeples:
            if m.id == meeple_id:
                m.active = False
                break

