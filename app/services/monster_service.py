from app.models.models import MonsterTemplate, Combatant, Character

class CombatantFactory:
    @staticmethod
    def create_from_monster_template(
        template: MonsterTemplate,
        encounter_id: str,
        custom_name: str = None
    ) -> Combatant:
        """
        Создает NPC-участника на основе шаблона монстра.
        Модификатор инициативы берётся из шаблона, а сам бросок d20 будет сгенерирован
        """
        return Combatant(
            encounter_id=encounter_id,
            monster_template_id=template.id,
            name=custom_name or template.name,
            is_npc=True,
            max_hp=template.max_hp,
            current_hp=template.max_hp,
            initiative_modifier=template.initiative_modifier,
            initiative_roll=None,
        )

    @staticmethod
    def create_from_character(
        character: Character,
        encounter_id: str,
        initiative_roll: int
    ) -> Combatant:
        """
        Создает участника-Игрока на основе персонажа.
        Значение initiative_roll передается вручную из ввода игрока.
        """
        return Combatant(
            encounter_id=encounter_id,
            character_id=character.id,
            name=character.name,
            is_npc=False,
            max_hp=character.max_hp,
            current_hp=character.max_hp,
            initiative_modifier=character.initiative_modifier,
            initiative_roll=initiative_roll,
        )