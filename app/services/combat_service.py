from typing import Optional, Tuple
from app.models.models import Combatant, Encounter, EncounterStatus
import datetime


class CombatService:
    @staticmethod
    def apply_hp_change(combatant: Combatant, amount: int) -> Tuple[int, bool]:
        """
        Изменяет HP участника:
        amount < 0 — урон
        amount > 0 — лечение
        Возвращает (новое_hp, статус_повержен)
        """
        combatant.current_hp += amount

        # Здоровье не может превышать max_hp
        if combatant.current_hp > combatant.max_hp:
            combatant.current_hp = combatant.max_hp

        # Ограничение снизу (0)
        if combatant.current_hp <= 0:
            combatant.current_hp = 0
            combatant.is_defeated = True
        else:
            combatant.is_defeated = False

        return combatant.current_hp, combatant.is_defeated

    @staticmethod
    def get_next_active_combatant(encounter: Encounter) -> Tuple[Optional[Combatant], int]:
        """
        Определяет, кто ходит следующим, пропуская поверженных (is_defeated = True).
        Возвращает (следующий_участник, номер_раунда).
        """
        # Берем только недееспособных участников с установленным turn_order
        active_combatants = [c for c in encounter.combatants if not c.is_defeated and c.turn_order is not None]
        active_combatants.sort(key=lambda x: x.turn_order)

        if not active_combatants:
            return None, encounter.current_round

        current_idx = -1
        for idx, c in enumerate(active_combatants):
            if c.id == encounter.active_combatant_id:
                current_idx = idx
                break

        next_idx = (current_idx + 1) % len(active_combatants)
        new_round = encounter.current_round

        # Если круг замкнулся — наступает следующий раунд
        if next_idx == 0 and current_idx != -1:
            new_round += 1

        return active_combatants[next_idx], new_round

    @staticmethod
    def check_and_finish_encounter(encounter: Encounter) -> bool:
        """
        Определяет окончен ли бой, все ли монстры повержены.
        Возвращает булево выражение.
        """
        monsters = [c for c in encounter.combatants if c.is_npc]
        if monsters and all(m.is_defeated for m in monsters):
            encounter.status = EncounterStatus.COMPLETED
            encounter.finished_at = datetime.datetime.now(datetime.timezone.utc)
            return True
        return False