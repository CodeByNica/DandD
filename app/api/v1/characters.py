import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_async_session
from app.models.models import Character
from app.schemas.schemas import CharacterCreate, CharacterRead, CharacterUpdate

router = APIRouter(prefix="/characters", tags=["Characters"])

@router.post("/", response_model=CharacterRead, status_code=status.HTTP_201_CREATED, description="Создание игрока")
async def create_character(
    char_data: CharacterCreate,
    session: AsyncSession = Depends(get_async_session)
):
    """
    Создание нового игрока
    """
    character = Character(**char_data.model_dump())
    session.add(character)
    await session.commit()
    await session.refresh(character)
    return character

@router.get("/", response_model=List[CharacterRead], description="Получение списка игроков")
async def list_characters(session: AsyncSession = Depends(get_async_session)):
    """
    Получение списка всех игроков
    """
    result = await session.execute(select(Character).order_by(Character.name))
    return result.scalars().all()

@router.get("/{character_id}", response_model=CharacterRead, description="Получение игрока")
async def get_character(
    character_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session)
):
    """
    Получение конкретного игрока по его идентификатору
    """
    character = await session.get(Character, character_id)
    if not character:
        raise HTTPException(status_code=404, detail="Персонаж не найден")
    return character

@router.patch("/{character_id}", response_model=CharacterRead, description="Обновление информации")
async def update_character(
    character_id: uuid.UUID,
    char_data: CharacterUpdate,
    session: AsyncSession = Depends(get_async_session)
):
    """
    Обновление информации об игроке
    """
    character = await session.get(Character, character_id)
    if not character:
        raise HTTPException(
            status_code=404,
            detail="Персонаж не найден"
        )
    update_data = char_data.model_dump(
        exclude_unset=True,
        exclude_none=True
    )
    if not update_data:
        raise HTTPException(
            status_code=400,
            detail="Не указаны данные для обновления"
        )
    for field, value in update_data.items():
        setattr(character, field, value)
    await session.commit()
    await session.refresh(character)
    return character

@router.delete("/{character_id}", status_code=status.HTTP_204_NO_CONTENT, description="Удаление персонажа")
async def delete_character(
    character_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session)
):
    """
    Удаление персонажа
    """
    character = await session.get(Character, character_id)
    if not character:
        raise HTTPException(status_code=404, detail="Персонаж не найден")
    await session.delete(character)
    await session.commit()