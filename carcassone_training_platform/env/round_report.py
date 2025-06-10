from dataclasses import dataclass, field
from typing import Dict, List, Any


@dataclass
class Event:
    type: str                # 事件类型（例如 TilePlaced、MeeplePlaced、ScoreUpdated、FeatureClosed）
    payload: Dict[str, Any]  # 每个事件的数据载荷（灵活、可扩展）


@dataclass
class RoundReport:
    events: List[Event] = field(default_factory=list)

    def add_event(self, event: Event):
        self.events.append(event)
    def reset(self):
        self.events.clear()

    def serialize(self):
        """
        简单序列化方便直接 jsonify 返回前端
        """
        return {
            "events": [
                {
                    "type": e.type,
                    "payload": e.payload
                } for e in self.events
            ]
        }
