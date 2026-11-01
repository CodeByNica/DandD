import uuid
import enum
from datetime import datetime
from typing import List, Optional
from sqlalchemy import String, Integer, Boolean, ForeignKey, Enum as SQLEnum, DateTime, func, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.database import Base
from pydantic import BaseModel


class EncounterStatus(str, enum.Enum):
    DRAFT = "draft"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"

class EncounterStatusUpdate(BaseModel):
    status: EncounterStatus

class ResolveTiesRequest(BaseModel):
    ordered_combatant_ids: List[uuid.UUID]

class DamageHealRequest(BaseModel):
    amount: int  # Положительное число для лечения, отрицательное для урона

class EventType(str, enum.Enum):
    DAMAGE = "damage"
    HEAL = "heal"
    INITIATIVE_ROLL = "initiative_roll"
    CONDITION_ADD = "condition_add"
    TURN_CHANGE = "turn_change"
    NOTE = "note"


class Character(Base):
    __tablename__ = "characters"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    type: Mapped[str] = mapped_column(String(20), default="player")  # player / npc
    initiative_modifier: Mapped[int] = mapped_column(Integer, default=0)
    max_hp: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    combatants: Mapped[List["Combatant"]] = relationship(back_populates="character")


class MonsterTemplate(Base):
    __tablename__ = "monster_templates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    type: Mapped[str] = mapped_column(String(20), default="npc")
    initiative_modifier: Mapped[int] = mapped_column(Integer, default=0)
    max_hp: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    combatants: Mapped[List["Combatant"]] = relationship(back_populates="monster_template")


class Encounter(Base):
    __tablename__ = "encounters"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    status: Mapped[EncounterStatus] = mapped_column(SQLEnum(EncounterStatus), default=EncounterStatus.DRAFT)
    current_round: Mapped[int] = mapped_column(Integer, default=1)
    active_combatant_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    combatants: Mapped[List["Combatant"]] = relationship(back_populates="encounter", cascade="all, delete-orphan")
    events: Mapped[List["CombatEvent"]] = relationship(back_populates="encounter", cascade="all, delete-orphan")


class Combatant(Base):
    __tablename__ = "combatants"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    encounter_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("encounters.id", ondelete="CASCADE"),
                                                    nullable=False)
    character_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True),
                                                              ForeignKey("characters.id", ondelete="SET NULL"),
                                                              nullable=True)
    monster_template_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True),
                                                                     ForeignKey("monster_templates.id",
                                                                                ondelete="SET NULL"), nullable=True)

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_npc: Mapped[bool] = mapped_column(Boolean, default=True)
    max_hp: Mapped[int] = mapped_column(Integer, nullable=False)
    current_hp: Mapped[int] = mapped_column(Integer, nullable=False)
    initiative_modifier: Mapped[int] = mapped_column(Integer, default=0)
    initiative_roll: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    total_initiative: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    turn_order: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_defeated: Mapped[bool] = mapped_column(Boolean, default=False)

    encounter: Mapped["Encounter"] = relationship(back_populates="combatants")
    character: Mapped[Optional["Character"]] = relationship(back_populates="combatants")
    monster_template: Mapped[Optional["MonsterTemplate"]] = relationship(back_populates="combatants")
    tie_break_roll: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    tie_break_total: Mapped[Optional[int]] = mapped_column(Integer,nullable=True)
    tie_break_resolved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class CombatEvent(Base):
    __tablename__ = "combat_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    encounter_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("encounters.id", ondelete="CASCADE"),
                                                    nullable=False)
    round: Mapped[int] = mapped_column(Integer, nullable=False)
    actor_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True),
                                                          ForeignKey("combatants.id", ondelete="SET NULL"),
                                                          nullable=True)
    target_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True),
                                                           ForeignKey("combatants.id", ondelete="SET NULL"),
                                                           nullable=True)
    event_type: Mapped[EventType] = mapped_column(SQLEnum(EventType), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    encounter: Mapped["Encounter"] = relationship(back_populates="events")
    actor: Mapped[Optional["Combatant"]] = relationship("Combatant", foreign_keys=[actor_id])
    target: Mapped[Optional["Combatant"]] = relationship("Combatant", foreign_keys=[target_id])