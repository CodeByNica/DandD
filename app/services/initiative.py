import random
from typing import List, Tuple
from app.models.models import Combatant


class InitiativeService:
    @staticmethod
    def roll_d20() -> int:
        """Бросок двадцатигранной кости d20 (1-20)."""
        return random.randint(1, 20)

    @classmethod
    def calculate_and_sort(cls, combatants: List[Combatant]) -> List[Combatant]:
        """
        1. Генерирует бросок d20 для NPC, если он еще не сделан.
        2. Считает total_initiative = roll + modifier.
        3. Сортирует по убыванию total_initiative, а при равенстве — по initiative_modifier.
        4. Проставляет первичный turn_order.
        """
        for c in combatants:
            if c.is_npc and c.initiative_roll is None:
                c.initiative_roll = cls.roll_d20()

            if c.initiative_roll is not None:
                c.total_initiative = c.initiative_roll + c.initiative_modifier

        # Первичная сортировка: сначала total_initiative, потом initiative_modifier
        sorted_list = sorted(
            combatants,
            key=lambda x: (x.total_initiative if x.total_initiative is not None else -99, x.initiative_modifier),
            reverse=True
        )

        for idx, c in enumerate(sorted_list, start=1):
            c.turn_order = idx

        return sorted_list

    @staticmethod
    def find_ties(combatants: List[Combatant]) -> List[List[Combatant]]:
        """
        Находит группы участников с полностью одинаковым total_initiative и initiative_modifier,
        требующие внимания Мастера в модальном окне Tie-Breaker.
        """
        groups = {}
        for c in combatants:
            key = (c.total_initiative, c.initiative_modifier)
            groups.setdefault(key, []).append(c)

        # Возвращаем только группы, где больше одного участника
        return [group for group in groups.values() if len(group) > 1]