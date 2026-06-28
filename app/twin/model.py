from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class DigitalTwinModel:
    user_id: str = "default"
    preferences: Dict[str, object] = field(default_factory=dict)
    communication_style: str = "casual"  # "casual" | "formal" | "technical"
    frequent_agents: Dict[str, int] = field(default_factory=dict)
    frequent_skills: Dict[str, int] = field(default_factory=dict)
    active_hours: List[int] = field(default_factory=list)   # raw hour samples (0-23)
    project_habits: Dict[str, dict] = field(default_factory=dict)
    decision_patterns: List[dict] = field(default_factory=list)  # capped at 50
    updated_at: str = ""

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "preferences": self.preferences,
            "communication_style": self.communication_style,
            "frequent_agents": self.frequent_agents,
            "frequent_skills": self.frequent_skills,
            "active_hours": self.active_hours,
            "project_habits": self.project_habits,
            "decision_patterns": self.decision_patterns,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DigitalTwinModel":
        return cls(
            user_id=data.get("user_id", "default"),
            preferences=data.get("preferences", {}),
            communication_style=data.get("communication_style", "casual"),
            frequent_agents=data.get("frequent_agents", {}),
            frequent_skills=data.get("frequent_skills", {}),
            active_hours=data.get("active_hours", []),
            project_habits=data.get("project_habits", {}),
            decision_patterns=data.get("decision_patterns", []),
            updated_at=data.get("updated_at", ""),
        )
