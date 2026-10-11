import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field
from app.models.models import EncounterStatus, EventType

class CharacterBase(BaseModel):
    name: str = Field(..., max_length=100)
    type: str = "player"
    initiative_modifier: int = 0
    max_hp: int = Field(..., gt=0)

class CharacterCreate(CharacterBase):
    pass

class CharacterRead(CharacterBase):
    id: uuid.UUID
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class MonsterTemplateBase(BaseModel):
    name: str = Field(..., max_length=100)
    type: str = "npc"
    initiative_modifier: int = 0
    max_hp: int = Field(..., gt=0)
    description: Optional[str] = None

class MonsterTemplateCreate(MonsterTemplateBase):
    pass

class MonsterTemplateRead(MonsterTemplateBase):
    id: uuid.UUID
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class CombatantCreate(BaseModel):
    character_id: Optional[uuid.UUID] = None
    monster_template_id: Optional[uuid.UUID] = None
    name: str
    is_npc: bool = True
    max_hp: int
    initiative_modifier: int = 0
    initiative_roll: Optional[int] = None  # Для игроков передается с фронта

class CombatantRead(BaseModel):
    id: uuid.UUID
    encounter_id: uuid.UUID
    character_id: Optional[uuid.UUID]
    monster_template_id: Optional[uuid.UUID]
    name: str
    is_npc: bool
    max_hp: int
    current_hp: int
    initiative_modifier: int
    initiative_roll: Optional[int]
    total_initiative: Optional[int]
    turn_order: Optional[int]
    is_defeated: bool
    model_config = ConfigDict(from_attributes=True)


class EncounterCreate(BaseModel):
    title: str = Field(..., max_length=150)

class EncounterRead(BaseModel):
    id: uuid.UUID
    title: str
    status: EncounterStatus
    current_round: int
    active_combatant_id: Optional[uuid.UUID]
    created_at: datetime
    finished_at: Optional[datetime]
    combatants: List[CombatantRead] = []
    model_config = ConfigDict(from_attributes=True)


class CombatEventRead(BaseModel):
    id: uuid.UUID
    encounter_id: uuid.UUID
    round: int
    actor_id: Optional[uuid.UUID]
    target_id: Optional[uuid.UUID]
    event_type: EventType
    payload: dict
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class AddCharacterCombatantRequest(BaseModel):
    character_id: uuid.UUID
    initiative_roll: int = Field(..., ge=1, le=20)

class AddMonsterCombatantRequest(BaseModel):
    monster_template_id: uuid.UUID
    custom_name: Optional[str] = None