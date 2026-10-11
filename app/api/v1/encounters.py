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


@router.post("/", response_model=EncounterRead, status_code=status.HTTP_201_CREATED)
async def create_encounter(
    encounter_data: EncounterCreate,
    session: AsyncSession = Depends(get_async_session)
):
    encounter = Encounter(title=encounter_data.title)
    session.add(encounter)
    await session.commit()

    return await _get_encounter_or_404(encounter.id, session)


@router.get("/", response_model=List[EncounterRead])
async def list_encounters(session: AsyncSession = Depends(get_async_session)):
    result = await session.execute(
        select(Encounter)
        .options(selectinload(Encounter.combatants))
        .order_by(Encounter.created_at.desc())
    )
    return result.scalars().all()


@router.get("/{encounter_id}", response_model=EncounterRead)
async def get_encounter(
    encounter_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session)
):
    return await _get_encounter_or_404(encounter_id, session)


@router.post("/{encounter_id}/combatants", response_model=EncounterRead)
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


@router.get("/{encounter_id}/export")
async def export_encounter_json(
    encounter_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session)
):
    """Экспорт боя и его истории в JSON с использованием ExportService."""
    encounter = await _get_encounter_or_404(encounter_id, session)

    events_result = await session.execute(
        select(CombatEvent)
        .where(CombatEvent.encounter_id == encounter_id)
        .order_by(CombatEvent.created_at.asc())
    )
    events = events_result.scalars().all()
    return ExportService.encounter_to_json(encounter, events)


# 1. Добавление Игрока в бой (с ручным броском d20)
@router.post("/{encounter_id}/combatants/character", response_model=EncounterRead)
async def add_character_to_encounter(
    encounter_id: uuid.UUID,
    body: AddCharacterCombatantRequest,
    session: AsyncSession = Depends(get_async_session)
):
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


# 2. Быстрое добавление Монстра из бестиария в 1 клик
@router.post("/{encounter_id}/combatants/monster", response_model=EncounterRead)
async def add_monster_to_encounter(
    encounter_id: uuid.UUID,
    body: AddMonsterCombatantRequest,
    session: AsyncSession = Depends(get_async_session)
):
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


@router.patch("/{encounter_id}/status", response_model=EncounterRead)
async def update_encounter_status(
        encounter_id: uuid.UUID,
        body: EncounterStatusUpdate,
        session: AsyncSession = Depends(get_async_session)
):
    encounter = await session.get(Encounter, encounter_id)
    if not encounter:
        raise HTTPException(status_code=404, detail="Бой не найден")
    encounter.status = body.status
    if body.status == EncounterStatus.COMPLETED and not encounter.finished_at:
        encounter.finished_at = datetime.datetime.now(datetime.timezone.utc)
    elif body.status != EncounterStatus.COMPLETED:
        encounter.finished_at = None
    await session.commit()
    return await _get_encounter_or_404(encounter_id, session)