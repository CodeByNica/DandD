import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_async_session
from app.models.models import Character
from app.schemas.schemas import CharacterCreate, CharacterRead

router = APIRouter(prefix="/characters", tags=["Characters"])

@router.post("/", response_model=CharacterRead, status_code=status.HTTP_201_CREATED)
async def create_character(
    char_data: CharacterCreate,
    session: AsyncSession = Depends(get_async_session)
):
    character = Character(**char_data.model_dump())
    session.add(character)
    await session.commit()
    await session.refresh(character)
    return character

@router.get("/", response_model=List[CharacterRead])
async def list_characters(session: AsyncSession = Depends(get_async_session)):
    result = await session.execute(select(Character).order_by(Character.name))
    return result.scalars().all()

@router.get("/{character_id}", response_model=CharacterRead)
async def get_character(
    character_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session)
):
    character = await session.get(Character, character_id)
    if not character:
        raise HTTPException(status_code=404, detail="Персонаж не найден")
    return character

@router.delete("/{character_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_character(
    character_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session)
):
    character = await session.get(Character, character_id)
    if not character:
        raise HTTPException(status_code=404, detail="Персонаж не найден")
    await session.delete(character)
    await session.commit()