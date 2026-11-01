import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_async_session
from app.models.models import MonsterTemplate
from app.schemas.schemas import MonsterTemplateCreate, MonsterTemplateRead, MonsterTemplateUpdate

router = APIRouter(prefix="/monsters", tags=["Monster Templates"])

@router.post("/", response_model=MonsterTemplateRead, status_code=status.HTTP_201_CREATED, description="Создание монстра")
async def create_monster_template(
    monster_data: MonsterTemplateCreate,
    session: AsyncSession = Depends(get_async_session)
):
    """
    Создание нового монстра в библиотеку
    """
    monster = MonsterTemplate(**monster_data.model_dump())
    session.add(monster)
    await session.commit()
    await session.refresh(monster)
    return monster

@router.get("/", response_model=List[MonsterTemplateRead], description="Получение всех монстров")
async def list_monster_templates(session: AsyncSession = Depends(get_async_session)):
    '''
    Получение списка монстров
    '''
    result = await session.execute(select(MonsterTemplate).order_by(MonsterTemplate.name))
    return result.scalars().all()

@router.get("/{monster_id}", response_model=MonsterTemplateRead, description="Получение 1 монстра")
async def get_monster_template(
    monster_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session)
):
    """
    Получение конкретного монстра по его идентификатору
    """
    monster = await session.get(MonsterTemplate, monster_id)
    if not monster:
        raise HTTPException(status_code=404, detail="Шаблон монстра не найден")
    return monster

@router.patch("/{monster_id}", response_model=MonsterTemplateRead, description="Обновление информации")
async def update_monster_template(
    monster_id: uuid.UUID,
    monster_data: MonsterTemplateUpdate,
    session: AsyncSession = Depends(get_async_session)
):
    """
    Обновление информации о монстрах в библиотеке
    """
    monster = await session.get(MonsterTemplate, monster_id)
    if not monster:
        raise HTTPException(
            status_code=404,
            detail="Шаблон монстра не найден"
        )
    update_data = monster_data.model_dump(
        exclude_unset=True,
        exclude_none=True
    )
    if not update_data:
        raise HTTPException(
            status_code=400,
            detail="Не указаны данные для обновления"
        )
    for field, value in update_data.items():
        setattr(monster, field, value)
    await session.commit()
    await session.refresh(monster)
    return monster

@router.delete("/{monster_id}", status_code=status.HTTP_204_NO_CONTENT, description="Удаление монстра")
async def delete_monster_template(
    monster_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session)
):
    """
    Удаление монстра из библиотеки
    """
    monster = await session.get(MonsterTemplate, monster_id)
    if not monster:
        raise HTTPException(status_code=404, detail="Шаблон монстра не найден")
    await session.delete(monster)
    await session.commit()