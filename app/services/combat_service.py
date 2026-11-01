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
        if combatant.current_hp > combatant.max_hp:
            combatant.current_hp = combatant.max_hp
        if combatant.current_hp <= 0:
            combatant.current_hp = 0
            combatant.is_defeated = True
        else:
            combatant.is_defeated = False

        return combatant.current_hp, combatant.is_defeated


    @staticmethod
    def get_next_active_combatant(
        encounter: Encounter
    ) -> Tuple[Optional[Combatant], int]:
        """
        Определяет следующего живого участника,
        сохраняя исходную последовательность ходов.
        Возвращает (следующий участник, номер раунда).
        """
        all_combatants = sorted(
            [
                c for c in encounter.combatants
                if c.turn_order is not None
            ],
            key=lambda c: c.turn_order
        )
        if not all_combatants:
            return None, encounter.current_round
        current_idx = next(
            (
                idx for idx, c in enumerate(all_combatants)
                if c.id == encounter.active_combatant_id
            ),
            None
        )
        if current_idx is None:
            for combatant in all_combatants:
                if not combatant.is_defeated:
                    return combatant, encounter.current_round

            return None, encounter.current_round
        total = len(all_combatants)
        for step in range(1, total + 1):
            next_idx = (current_idx + step) % total
            candidate = all_combatants[next_idx]
            if not candidate.is_defeated:
                new_round = encounter.current_round
                if next_idx <= current_idx:
                    new_round += 1
                return candidate, new_round
        return None, encounter.current_round

    @staticmethod
    def check_and_finish_encounter(encounter: Encounter) -> bool:
        """
        Проверяет, завершён ли бой.
        Бой автоматически завершается, если:
        - все NPC повержены;
        - все персонажи игроков повержены
        Автоматическая проверка выполняется только для боя
        со статусом IN_PROGRESS.
        Возвращает True, если бой завершён, иначе False.
        """

        if encounter.status == EncounterStatus.COMPLETED:
            return True
        if encounter.status != EncounterStatus.IN_PROGRESS:
            return False
        monsters = [c for c in encounter.combatants if c.is_npc]
        players = [c for c in encounter.combatants if not c.is_npc]
        all_monsters_defeated = (
            bool(monsters) and all(m.is_defeated for m in monsters)
        )
        all_players_defeated = (
            bool(players) and all(p.is_defeated for p in players)
        )
        if all_monsters_defeated or all_players_defeated:
            encounter.status = EncounterStatus.COMPLETED
            encounter.finished_at = datetime.datetime.now(
                datetime.timezone.utc
            )
            encounter.active_combatant_id = None
            return True
        return False
