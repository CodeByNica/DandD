import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
import datetime
from app.database import get_async_session
from app.models.models import Encounter, Combatant, CombatEvent, Character, MonsterTemplate, EncounterStatus, EncounterStatusUpdate
from app.schemas.schemas import (
    EncounterCreate,
    EncounterRead,
    CombatantCreate,
    AddCharacterCombatantRequest,
    AddMonsterCombatantRequest,
)
from app.services.monster_service import CombatantFactory
from app.services.export_service import ExportService

router = APIRouter(prefix="/encounters", tags=["Encounters"])


async def _get_encounter_or_404(
    encounter_id: uuid.UUID, session: AsyncSession
) -> Encounter:
    """Вспомогательная функция для получения боя с подгруженными участниками."""
    result = await session.execute(
        select(Encounter)
        .options(selectinload(Encounter.combatants))
        .where(Encounter.id == encounter_id)
    )
    encounter = result.scalar_one_or_none()
    if not encounter:
        raise HTTPException(status_code=404, detail="Бой не найден")
    return encounter


@router.post("/", response_model=EncounterRead, status_code=status.HTTP_201_CREATED, description="Создание сражения")
async def create_encounter(
    encounter_data: EncounterCreate,
    session: AsyncSession = Depends(get_async_session)
):
    """
     Создаёт новое сражение с заданным названием и начальным статусом.
    """
    encounter = Encounter(title=encounter_data.title)
    session.add(encounter)
    await session.commit()

    return await _get_encounter_or_404(encounter.id, session)


@router.get("/", response_model=List[EncounterRead], description="	Получение списка сражений")
async def list_encounters(session: AsyncSession = Depends(get_async_session)):
    """
    Возвращает список всех созданных сражений с информацией об их участниках.
    """
    result = await session.execute(
        select(Encounter)
        .options(selectinload(Encounter.combatants))
        .order_by(Encounter.created_at.desc())
    )
    return result.scalars().all()


@router.get("/{encounter_id}", response_model=EncounterRead, description="Получение сражения")
async def get_encounter(
    encounter_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session)
):
    '''
    Возвращает подробную информацию о выбранном сражении и его участниках по идентификатору.
    '''
    return await _get_encounter_or_404(encounter_id, session)


@router.post("/{encounter_id}/combatants", response_model=EncounterRead, description="Ручное добавление участника")
async def add_combatant(
    encounter_id: uuid.UUID,
    combatant_data: CombatantCreate,
    session: AsyncSession = Depends(get_async_session)
):
    """Прямое/ручное добавление участника без использования шаблонов."""
    await _get_encounter_or_404(encounter_id, session)

    combatant = Combatant(
        encounter_id=encounter_id,
        character_id=combatant_data.character_id,
        monster_template_id=combatant_data.monster_template_id,
        name=combatant_data.name,
        is_npc=combatant_data.is_npc,
        max_hp=combatant_data.max_hp,
        current_hp=combatant_data.max_hp,
        initiative_modifier=combatant_data.initiative_modifier,
        initiative_roll=combatant_data.initiative_roll,
    )
    session.add(combatant)
    await session.commit()

    return await _get_encounter_or_404(encounter_id, session)

@router.post("/{encounter_id}/combatants/character", response_model=EncounterRead, description="Добавление персонажа")
async def add_character_to_encounter(
    encounter_id: uuid.UUID,
    body: AddCharacterCombatantRequest,
    session: AsyncSession = Depends(get_async_session)
):
    '''
    Добавляет существующего персонажа в сражение,
    используя его характеристики и переданный результат броска инициативы.
    '''
    encounter = await _get_encounter_or_404(encounter_id, session)
    character = await session.get(Character, body.character_id)
    if not character:
        raise HTTPException(status_code=404, detail="Персонаж не найден")

    combatant = CombatantFactory.create_from_character(
        character=character,
        encounter_id=encounter_id,
        initiative_roll=body.initiative_roll
    )
    session.add(combatant)
    await session.commit()

    return await _get_encounter_or_404(encounter_id, session)


@router.post("/{encounter_id}/combatants/monster", response_model=EncounterRead, description="Добавление монстра")
async def add_monster_to_encounter(
    encounter_id: uuid.UUID,
    body: AddMonsterCombatantRequest,
    session: AsyncSession = Depends(get_async_session)
):
    '''
    Добавляет монстра из бестиария в сражение на основе выбранного шаблона.
    Позволяет задать индивидуальное имя участника.
    '''
    encounter = await _get_encounter_or_404(encounter_id, session)
    template = await session.get(MonsterTemplate, body.monster_template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Шаблон монстра не найден")

    combatant = CombatantFactory.create_from_monster_template(
        template=template,
        encounter_id=encounter_id,
        custom_name=body.custom_name
    )
    session.add(combatant)
    await session.commit()

    return await _get_encounter_or_404(encounter_id, session)


@router.patch("/{encounter_id}/status", response_model=EncounterRead, description="Изменение статуса сражения.")
async def update_encounter_status(
        encounter_id: uuid.UUID,
        body: EncounterStatusUpdate,
        session: AsyncSession = Depends(get_async_session)
):
    """
    Изменяет текущий статус сражения.
    При завершении боя фиксирует дату и время завершения и сбрасывает активного участника.
    """
    encounter = await session.get(Encounter, encounter_id)
    if not encounter:
        raise HTTPException(status_code=404, detail="Бой не найден")
    encounter.status = body.status
    if body.status == EncounterStatus.COMPLETED:
        if encounter.finished_at is None:
            encounter.finished_at = datetime.datetime.now(
                datetime.timezone.utc
            )
        encounter.active_combatant_id = None
    else:
        encounter.finished_at = None
    await session.commit()
    return await _get_encounter_or_404(encounter_id, session)

@router.delete(
    "/{encounter_id}/combatants/{combatant_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    description="Удаляет участника из сражения"
)
async def remove_combatant(
    encounter_id: uuid.UUID,
    combatant_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session)
):
    """
    Удаляет выбранного участника из сражения по идентификатору.
    Исходная запись персонажа или шаблона монстра сохраняется.
    """
    encounter = await _get_encounter_or_404(encounter_id, session)

    combatant = next(
        (c for c in encounter.combatants if c.id == combatant_id),
        None
    )
    if not combatant:
        raise HTTPException(
            status_code=404,
            detail="Участник не найден в этом бою"
        )

    if encounter.active_combatant_id == combatant_id:
        encounter.active_combatant_id = None
    deleted_order = combatant.turn_order
    await session.delete(combatant)
    if deleted_order is not None:
        for c in encounter.combatants:
            if c.id != combatant_id and c.turn_order is not None:
                if c.turn_order > deleted_order:
                    c.turn_order -= 1

    await session.commit()

@router.get("/{encounter_id}/export", description="Экспорт сражения")
async def export_encounter_json(
    encounter_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session)
):
    """
    Экспорт боя и его истории в JSON
    """
    encounter = await _get_encounter_or_404(encounter_id, session)

    events_result = await session.execute(
        select(CombatEvent)
        .where(CombatEvent.encounter_id == encounter_id)
        .order_by(CombatEvent.created_at.asc())
    )
    events = events_result.scalars().all()
    return ExportService.encounter_to_json(encounter, events)