import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_async_session
from app.models.models import MonsterTemplate
from app.schemas.schemas import MonsterTemplateCreate, MonsterTemplateRead

router = APIRouter(prefix="/monsters", tags=["Monster Templates"])

@router.post("/", response_model=MonsterTemplateRead, status_code=status.HTTP_201_CREATED)
async def create_monster_template(
    monster_data: MonsterTemplateCreate,
    session: AsyncSession = Depends(get_async_session)
):
    monster = MonsterTemplate(**monster_data.model_dump())
    session.add(monster)
    await session.commit()
    await session.refresh(monster)
    return monster

@router.get("/", response_model=List[MonsterTemplateRead])
async def list_monster_templates(session: AsyncSession = Depends(get_async_session)):
    result = await session.execute(select(MonsterTemplate).order_by(MonsterTemplate.name))
    return result.scalars().all()

@router.get("/{monster_id}", response_model=MonsterTemplateRead)
async def get_monster_template(
    monster_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session)
):
    monster = await session.get(MonsterTemplate, monster_id)
    if not monster:
        raise HTTPException(status_code=404, detail="Шаблон монстра не найден")
    return monster

@router.delete("/{monster_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_monster_template(
    monster_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session)
):
    monster = await session.get(MonsterTemplate, monster_id)
    if not monster:
        raise HTTPException(status_code=404, detail="Шаблон монстра не найден")
    await session.delete(monster)
    await session.commit()