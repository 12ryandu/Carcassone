from typing import List
from env.player import Player
from env.round_report import RoundReport, Event

class RoundManager:
    def __init__(self, players: List[Player]):
        self.players = players
        self.current_player_index = 0
        self.round_count = 1  # ⚠️ 保持你的逻辑，初始从 1 开始
        self.round_report = RoundReport()
        self.action_pipe = []  # ✅ 保留你的 action pipe，未来可用

    # ✅ 回合控制逻辑
    def get_current_player(self) -> Player:
        return self.players[self.current_player_index]

    def get_current_player_index(self) -> int:
        return self.current_player_index

    def next_player(self):
        self.current_player_index += 1
        if self.current_player_index >= len(self.players):
            self.current_player_index = 0
            self.round_count += 1
        print(f"🎯 当前是第 {self.round_count} 回合，轮到玩家 {self.get_current_player().name}")

    def reset(self):
        self.current_player_index = 0
        self.round_count = 1
        print("🔄 回合管理器已重置")

    def restart(self):
        self.reset()

    def __str__(self):
        return f"Round {self.round_count}, Player: {self.get_current_player().name} (index {self.current_player_index})"

    # ✅ 事件日志系统
    def log_tile_placement(self, coord, tile_id, rotation):
        self.round_report.add_event(Event(
            type="TilePlaced",
            payload={"coord": coord, "tile_id": tile_id, "rotation": rotation}
        ))

    def log_meeple_placement(self, coord, feature_type, feature_id, meeple_type, player):
        self.round_report.add_event(Event(
            type="MeeplePlaced",
            payload={
                "coord": coord,
                "feature_type": feature_type,
                "feature_id": feature_id,
                "meeple_type": meeple_type,
                "player": player
            }
        ))

    def log_meeple_return(self, meeple_id, player):
        self.round_report.add_event(Event(
            type="MeepleReturned",
            payload={"meeple_id": meeple_id, "player": player}
        ))

    def log_score_change(self, player, delta_score):
        self.round_report.add_event(Event(
            type="ScoreUpdated",
            payload={"player": player, "score_delta": delta_score}
        ))

    # ✅ action pipe 预留（以后扩展特殊机制时用）
    def action_pipe_update(self):
        pass
