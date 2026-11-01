import random
from typing import List, Dict
from uuid import UUID
from app.models.models import Combatant

class InitiativeService:

    @staticmethod
    def roll_d20() -> int:
        """Бросок кости."""
        return random.randint(1, 20)

    @classmethod
    def calculate_and_sort(
        cls,
        combatants: List[Combatant]
    ) -> List[Combatant]:
        """
        Первичный расчёт инициативы.
        """
        for combatant in combatants:

            if combatant.is_npc and combatant.initiative_roll is None:
                combatant.initiative_roll = cls.roll_d20()

            if not combatant.is_npc and combatant.initiative_roll is None:
                raise ValueError(
                    f"Не задан бросок инициативы игрока: {combatant.name}"
                )
            combatant.total_initiative = (
                combatant.initiative_roll +
                combatant.initiative_modifier
            )
            combatant.tie_break_roll = None
            combatant.tie_break_total = None
            combatant.tie_break_resolved = False
        sorted_combatants = sorted(
            combatants,
            key=lambda c: c.total_initiative,
            reverse=True
        )
        for index, combatant in enumerate(sorted_combatants, start=1):
            combatant.turn_order = index
        return sorted_combatants

    @staticmethod
    def find_ties(
        combatants: List[Combatant]
    ) -> List[List[Combatant]]:
        """
        Находит только те группы, в которых ничья ещё не разрешена.
        """
        primary_groups = {}
        for combatant in combatants:
            if combatant.total_initiative is None:
                continue
            primary_groups.setdefault(
                combatant.total_initiative, []
            ).append(combatant)
        unresolved_groups = []
        for primary_group in primary_groups.values():
            if len(primary_group) < 2:
                continue
            pending = [
                c for c in primary_group
                if not c.tie_break_resolved
            ]
            if len(pending) < 2:
                continue
            tie_break_groups = {}
            for combatant in pending:
                tie_break_groups.setdefault(
                    combatant.tie_break_total, []
                ).append(combatant)
            for group in tie_break_groups.values():
                if len(group) > 1:
                    unresolved_groups.append(group)
        return unresolved_groups

    @classmethod
    def resolve_ties(
        cls,
        combatants: List[Combatant],
        player_rolls: Dict[UUID, int]
    ) -> List[Combatant]:
        """
        Разрешает текущие ничьи.
        Первичная инициатива не изменяется.
        """
        ties = cls.find_ties(combatants)
        if not ties:
            raise ValueError("Нет неразрешённых ничьих.")
        expected_player_ids = {
            c.id
            for group in ties
            for c in group
            if not c.is_npc
        }
        if set(player_rolls.keys()) != expected_player_ids:
            raise ValueError(
                "Необходимо передать результаты бросков "
                "всех игроков, участвующих в переброске."
            )
        for roll in player_rolls.values():
            if not isinstance(roll, int) or not 1 <= roll <= 20:
                raise ValueError("Результат броска должен быть от 1 до 20.")
        for group in ties:
            positions = sorted(
                c.turn_order for c in group
            )
            for combatant in group:
                if combatant.is_npc:
                    roll = cls.roll_d20()
                else:
                    roll = player_rolls[combatant.id]
                combatant.tie_break_roll = roll
                combatant.tie_break_total = (
                    roll + combatant.initiative_modifier
                )
            sorted_group = sorted(
                group,
                key=lambda c: c.tie_break_total,
                reverse=True
            )
            for position, combatant in zip(positions, sorted_group):
                combatant.turn_order = position
            result_groups = {}
            for combatant in group:
                result_groups.setdefault(
                    combatant.tie_break_total, []
                ).append(combatant)
            for result_group in result_groups.values():
                if len(result_group) == 1:
                    result_group[0].tie_break_resolved = True
                else:
                    for combatant in result_group:
                        combatant.tie_break_resolved = False
        return sorted(
            combatants,
            key=lambda c: c.turn_order
        )