import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from app.config import settings
from app.twin.model import DigitalTwinModel
from app.utils import logger

_TWIN_FILE = lambda: settings.get_data_path() / "twin" / "model.json"


class DigitalTwinTracker:
    def __init__(self):
        _twin_dir = settings.get_data_path() / "twin"
        _twin_dir.mkdir(parents=True, exist_ok=True)
        self._model = self._load()

    def _load(self) -> DigitalTwinModel:
        f = _TWIN_FILE()
        if f.exists():
            try:
                return DigitalTwinModel.from_dict(json.loads(f.read_text()))
            except Exception as e:
                logger.warning(f"DigitalTwin: load failed: {e}")
        return DigitalTwinModel()

    def _save(self):
        self._model.updated_at = datetime.now(timezone.utc).isoformat()
        _TWIN_FILE().write_text(json.dumps(self._model.to_dict(), indent=2))

    def record_agent_use(self, agent_type: str):
        self._model.frequent_agents[agent_type] = self._model.frequent_agents.get(agent_type, 0) + 1
        self.record_active_hour()
        self._save()

    def record_skill_use(self, skill_name: str):
        self._model.frequent_skills[skill_name] = self._model.frequent_skills.get(skill_name, 0) + 1
        self._save()

    def record_active_hour(self):
        hour = datetime.now().hour
        hours = self._model.active_hours
        hours.append(hour)
        if len(hours) > 1000:
            hours[:] = hours[-1000:]
        self._model.active_hours = hours
        self._save()

    def record_decision(self, context: str, choice: str):
        self._model.decision_patterns.append({
            "context": context[:300],
            "choice": choice[:200],
            "ts": datetime.now(timezone.utc).isoformat(),
        })
        if len(self._model.decision_patterns) > 50:
            self._model.decision_patterns = self._model.decision_patterns[-50:]
        self._save()

    def infer_style(self, messages: List[str]) -> str:
        if not messages:
            return self._model.communication_style
        code_blocks = sum(1 for m in messages if "```" in m or "`" in m)
        code_ratio = code_blocks / len(messages)
        if code_ratio > 0.2:
            style = "technical"
        else:
            word_counts = []
            for m in messages:
                sentences = re.split(r"[.!?]+", m)
                for s in sentences:
                    words = s.split()
                    if words:
                        word_counts.append(len(words))
            avg = sum(word_counts) / len(word_counts) if word_counts else 0
            style = "formal" if avg > 15 else "casual"
        self._model.communication_style = style
        self._save()
        return style

    def update_preference(self, key: str, value):
        self._model.preferences[key] = value
        self._save()

    def update_project_habit(self, project_id: str, session_minutes: float = 0):
        habits = self._model.project_habits
        if project_id not in habits:
            habits[project_id] = {"last_active": "", "task_count": 0, "avg_session_min": 0.0, "_session_count": 0}
        h = habits[project_id]
        h["last_active"] = datetime.now(timezone.utc).isoformat()
        h["task_count"] = h.get("task_count", 0) + 1
        if session_minutes > 0:
            n = h.get("_session_count", 0) + 1
            h["avg_session_min"] = (h.get("avg_session_min", 0.0) * (n - 1) + session_minutes) / n
            h["_session_count"] = n
        self._save()

    def get_model(self) -> DigitalTwinModel:
        return self._model

    def get_summary(self) -> dict:
        m = self._model
        top_agents = sorted(m.frequent_agents.items(), key=lambda x: x[1], reverse=True)[:5]
        top_skills = sorted(m.frequent_skills.items(), key=lambda x: x[1], reverse=True)[:5]
        hour_counts = Counter(m.active_hours)
        peak_hours = [h for h, _ in hour_counts.most_common(3)]
        return {
            "communication_style": m.communication_style,
            "top_agents": [{"agent": a, "uses": c} for a, c in top_agents],
            "top_skills": [{"skill": s, "uses": c} for s, c in top_skills],
            "peak_hours": sorted(peak_hours),
            "active_projects": len(m.project_habits),
            "preferences": m.preferences,
            "decisions_logged": len(m.decision_patterns),
            "updated_at": m.updated_at,
        }

    def reset(self):
        self._model = DigitalTwinModel()
        self._save()
        logger.info("DigitalTwin: model reset by user")


_tracker: Optional[DigitalTwinTracker] = None


def get_twin_tracker() -> DigitalTwinTracker:
    global _tracker
    if _tracker is None:
        _tracker = DigitalTwinTracker()
    return _tracker
