import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.database import get_async_session
from app.models.models import Encounter, Combatant, CombatEvent, EncounterStatus, EventType
from app.schemas.schemas import EncounterRead
from app.services.initiative import InitiativeService
from app.services.combat_service import CombatService

router = APIRouter(prefix="/combat", tags=["Combat Management"])


class ResolveTiesRequest(BaseModel):
    # Порядок ID участников в желаемой последовательности ходов при совпадении
    ordered_combatant_ids: List[uuid.UUID]


class DamageHealRequest(BaseModel):
    amount: int  # Положительное число для урона, отрицательное для лечения


async def _get_encounter_with_combatants(encounter_id: uuid.UUID, session: AsyncSession) -> Encounter:
    """Вспомогательная функция для получения боя с загруженными участниками."""
    result = await session.execute(
        select(Encounter)
        .options(selectinload(Encounter.combatants))
        .where(Encounter.id == encounter_id)
    )
    encounter = result.scalar_one_or_none()
    if not encounter:
        raise HTTPException(status_code=404, detail="Бой не найден")
    encounter.combatants.sort(
        key=lambda c: (c.turn_order is None, c.turn_order)
    )
    return encounter


@router.post("/{encounter_id}/roll-initiative", response_model=EncounterRead)
async def roll_and_sort_initiative(
    encounter_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session)
):
    """Генерация d20 для NPC, расчёт total_initiative и первичная сортировка."""
    encounter = await _get_encounter_with_combatants(encounter_id, session)

    sorted_combatants = InitiativeService.calculate_and_sort(encounter.combatants)

    encounter.status = EncounterStatus.IN_PROGRESS
    if sorted_combatants and not encounter.active_combatant_id:
        encounter.active_combatant_id = sorted_combatants[0].id

    await session.commit()
    return await _get_encounter_with_combatants(encounter_id, session)


@router.post("/{encounter_id}/resolve-ties", response_model=EncounterRead)
async def resolve_ties(
    encounter_id: uuid.UUID,
    body: ResolveTiesRequest,
    session: AsyncSession = Depends(get_async_session)
):
    """Применение порядка ходов из модального окна Tie-Breaker."""
    encounter = await _get_encounter_with_combatants(encounter_id, session)

    combatants_map = {c.id: c for c in encounter.combatants}
    for idx, c_id in enumerate(body.ordered_combatant_ids, start=1):
        if c_id in combatants_map:
            combatants_map[c_id].turn_order = idx

    await session.commit()
    return await _get_encounter_with_combatants(encounter_id, session)


@router.post("/{encounter_id}/combatants/{combatant_id}/hp", response_model=EncounterRead)
async def update_hp(
    encounter_id: uuid.UUID,
    combatant_id: uuid.UUID,
    body: DamageHealRequest,
    session: AsyncSession = Depends(get_async_session)
):
    """Изменение HP (+/- урон или лечение) и автопереключение состояния повержен (is_defeated)."""
    combatant = await session.get(Combatant, combatant_id)
    if not combatant or combatant.encounter_id != encounter_id:
        raise HTTPException(status_code=404, detail="Участник боя не найден")

    encounter = await session.get(Encounter, encounter_id)

    # Применяем изменение HP
    new_hp, is_defeated = CombatService.apply_hp_change(combatant, body.amount)
    CombatService.check_and_finish_encounter(encounter)

    # Записываем событие в лог
    event_type = EventType.DAMAGE if body.amount < 0 else EventType.HEAL
    event = CombatEvent(
        encounter_id=encounter_id,
        round=encounter.current_round,
        actor_id=None,
        target_id=combatant_id,
        event_type=event_type,
        payload={"amount": abs(body.amount), "new_hp": new_hp}
    )
    session.add(event)
    await session.commit()
    return await _get_encounter_with_combatants(encounter_id, session)


@router.post("/{encounter_id}/next-turn", response_model=EncounterRead)
async def next_turn(
    encounter_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session)
):
    """Передача хода следующему участнику (с учётом раундов и пропуска поверженных)."""
    encounter = await _get_encounter_with_combatants(encounter_id, session)
    if CombatService.check_and_finish_encounter(encounter):
        await session.commit()
        return encounter
    # Определяем следующего участника
    next_combatant, updated_round = CombatService.get_next_active_combatant(encounter)
    if not next_combatant:
        raise HTTPException(status_code=400, detail="В бою нет дееспособных участников")
    encounter.current_round = updated_round
    encounter.active_combatant_id = next_combatant.id
    # Записываем переход хода в лог
    event = CombatEvent(
        encounter_id=encounter_id,
        round=encounter.current_round,
        actor_id=encounter.active_combatant_id,
        event_type=EventType.TURN_CHANGE,
        payload={"next_round": encounter.current_round}
    )
    session.add(event)
    await session.commit()
    return await _get_encounter_with_combatants(encounter_id, session)