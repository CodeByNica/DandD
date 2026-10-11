import json
from typing import Dict, Any
from app.models.models import Encounter, CombatEvent

class ExportService:
    @staticmethod
    def encounter_to_json(encounter: Encounter, events: list[CombatEvent]) -> Dict[str, Any]:
        """Формирует готовый полный словарь для выгрузки боя в JSON."""
        return {
            "encounter": {
                "id": str(encounter.id),
                "title": encounter.title,
                "status": encounter.status.value,
                "current_round": encounter.current_round,
                "created_at": encounter.created_at.isoformat() if encounter.created_at else None,
                "finished_at": encounter.finished_at.isoformat() if encounter.finished_at else None,
            },
            "combatants": [
                {
                    "id": str(c.id),
                    "name": c.name,
                    "is_npc": c.is_npc,
                    "max_hp": c.max_hp,
                    "current_hp": c.current_hp,
                    "total_initiative": c.total_initiative,
                    "turn_order": c.turn_order,
                    "is_defeated": c.is_defeated,
                }
                for c in encounter.combatants
            ],
            "history_log": [
                {
                    "id": str(e.id),
                    "round": e.round,
                    "actor_id": str(e.actor_id) if e.actor_id else None,
                    "target_id": str(e.target_id) if e.target_id else None,
                    "event_type": e.event_type.value,
                    "payload": e.payload,
                    "created_at": e.created_at.isoformat() if e.created_at else None,
                }
                for e in events
            ]
        }