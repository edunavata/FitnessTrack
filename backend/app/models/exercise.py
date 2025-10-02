"""Exercise catalog models with enums, aliases, and tags."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.extensions import db

from .base import PKMixin, ReprMixin, TimestampMixin

if TYPE_CHECKING:
    from .exercise_secondary import ExerciseSecondaryMuscle

# --- Domain Enums ---
MuscleGroup = Enum(
    "CHEST",
    "BACK",
    "SHOULDERS",
    "QUADS",
    "HAMSTRINGS",
    "GLUTES",
    "CALVES",
    "BICEPS",
    "TRICEPS",
    "FOREARMS",
    "ABS",
    "OBLIQUES",
    "FULL_BODY",
    "OTHER",
    name="muscle_group",
)

Equipment = Enum(
    "BARBELL",
    "DUMBBELL",
    "MACHINE",
    "CABLE",
    "BODYWEIGHT",
    "KETTLEBELL",
    "BAND",
    "SMITH",
    "TRAP_BAR",
    "EZ_BAR",
    "PLATE",
    "OTHER",
    name="equipment",
)

Mechanics = Enum("COMPOUND", "ISOLATION", name="mechanics")

ForceVector = Enum("PUSH", "PULL", "STATIC", name="force_vector")

Level = Enum("BEGINNER", "INTERMEDIATE", "ADVANCED", name="level")

MovementPattern = Enum(
    "HINGE",
    "SQUAT",
    "LUNGE",
    "HORIZONTAL_PUSH",
    "HORIZONTAL_PULL",
    "VERTICAL_PUSH",
    "VERTICAL_PULL",
    "CARRY",
    "ROTATION",
    "ANTI_ROTATION",
    "HIP_ABDUCTION",
    "HIP_ADDUCTION",
    "CALF_RAISE",
    "CORE_BRACE",
    "OTHER",
    name="movement_pattern",
)


class Exercise(PKMixin, ReprMixin, TimestampMixin, db.Model):
    """Catalog of exercises with biomechanical metadata."""

    __tablename__ = "exercises"

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(140), nullable=False)

    primary_muscle: Mapped[str] = mapped_column(MuscleGroup, nullable=False)
    movement: Mapped[str] = mapped_column(MovementPattern, nullable=False)
    mechanics: Mapped[str] = mapped_column(Mechanics, nullable=False)
    force: Mapped[str] = mapped_column(ForceVector, nullable=False)
    unilateral: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    equipment: Mapped[str] = mapped_column(Equipment, nullable=False)

    grip: Mapped[str | None] = mapped_column(String(50))
    range_of_motion: Mapped[str | None] = mapped_column(Text)
    difficulty: Mapped[str] = mapped_column(Level, nullable=False, server_default="BEGINNER")
    cues: Mapped[str | None] = mapped_column(Text)
    instructions: Mapped[str | None] = mapped_column(Text)
    video_url: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")

    __table_args__ = (
        Index("ix_exercises_name", "name"),
        UniqueConstraint("slug", name="uq_exercises_slug"),
        CheckConstraint("length(slug) > 0", name="ck_exercises_slug_not_empty"),
    )

    # Relationships
    aliases: Mapped[list[ExerciseAlias]] = relationship(
        "ExerciseAlias",
        back_populates="exercise",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    tags: Mapped[list[ExerciseTag]] = relationship(
        "ExerciseTag",
        back_populates="exercise",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    secondary_muscles: Mapped[list[ExerciseSecondaryMuscle]] = db.relationship(
        "ExerciseSecondaryMuscle",
        back_populates="exercise",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
    )


class ExerciseAlias(PKMixin, ReprMixin, TimestampMixin, db.Model):
    """Alternative names for exercises."""

    __tablename__ = "exercise_aliases"

    exercise_id: Mapped[int] = mapped_column(
        ForeignKey("exercises.id", ondelete="CASCADE"), nullable=False
    )
    alias: Mapped[str] = mapped_column(String(120), nullable=False)

    __table_args__ = (UniqueConstraint("exercise_id", "alias", name="uq_exercise_alias"),)

    # Relationship
    exercise: Mapped[Exercise] = relationship("Exercise", back_populates="aliases")


class Tag(PKMixin, ReprMixin, TimestampMixin, db.Model):
    """Curated free-form tags."""

    __tablename__ = "tags"

    name: Mapped[str] = mapped_column(String(50), nullable=False)

    __table_args__ = (UniqueConstraint("name", name="uq_tags_name"),)

    # Relationship
    exercises: Mapped[list[ExerciseTag]] = relationship(
        "ExerciseTag",
        back_populates="tag",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class ExerciseTag(TimestampMixin, ReprMixin, db.Model):
    """Many-to-many join table for exercises and tags."""

    __tablename__ = "exercise_tags"

    exercise_id: Mapped[int] = mapped_column(
        ForeignKey("exercises.id", ondelete="CASCADE"), primary_key=True
    )
    tag_id: Mapped[int] = mapped_column(ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True)

    __table_args__ = (UniqueConstraint("exercise_id", "tag_id", name="uq_exercise_tag"),)

    # Relationships
    exercise: Mapped[Exercise] = relationship("Exercise", back_populates="tags")
    tag: Mapped[Tag] = relationship("Tag", back_populates="exercises")
