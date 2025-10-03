"""Subject, SubjectProfile, and SubjectBodyMetrics models."""

from __future__ import annotations

from datetime import date
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.core.extensions import db

from .base import PKMixin, ReprMixin, TimestampMixin

if TYPE_CHECKING:
    from .cycle import Cycle
    from .exercise_log import ExerciseSetLog
    from .routine import Routine, SubjectRoutine
    from .workout import WorkoutSession


class Subject(PKMixin, ReprMixin, TimestampMixin, db.Model):
    """
    Pseudonymous subject entity used across the domain.

    Holds a stable pseudonymous identifier and an optional 1:1 link to ``User``.
    Breaking the link (``user_id = NULL``) supports anonymization while
    preserving domain analytics.
    """

    __tablename__ = "subjects"

    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, unique=True
    )
    pseudonym: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, default=uuid4)

    # ---------------- Relationships ----------------
    user = relationship("User", uselist=False, backref="subject", passive_deletes=True)

    profile = relationship(
        "SubjectProfile",
        uselist=False,
        back_populates="subject",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    body_metrics = relationship(
        "SubjectBodyMetrics",
        back_populates="subject",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    # 🔹 Nueva relación principal: SubjectRoutine
    subject_routines: Mapped[list[SubjectRoutine]] = relationship(
        "SubjectRoutine",
        back_populates="subject",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
    )

    # 🔹 Atajo de solo lectura a rutinas
    saved_routines: Mapped[list[Routine]] = relationship(
        "Routine",
        secondary="subject_routines",
        viewonly=True,
        lazy="selectin",
    )

    # 🔹 Rutinas creadas por este subject (propietario)
    owned_routines: Mapped[list[Routine]] = relationship(
        "Routine",
        back_populates="owner",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
    )

    cycles: Mapped[list[Cycle]] = relationship(
        "Cycle",
        back_populates="subject",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
    )
    workouts: Mapped[list[WorkoutSession]] = relationship(
        "WorkoutSession",
        back_populates="subject",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
    )
    exercise_logs: Mapped[list[ExerciseSetLog]] = relationship(
        "ExerciseSetLog",
        back_populates="subject",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
    )

    __table_args__ = (
        UniqueConstraint("user_id", name="uq_subjects_user"),
        UniqueConstraint("pseudonym", name="uq_subjects_pseudonym"),
        Index("ix_subjects_user_id", "user_id"),
        Index("ix_subjects_pseudonym", "pseudonym"),
    )


class SexEnum(str, Enum):
    """Sex enumeration aligned with DB schema."""

    MALE = "MALE"
    FEMALE = "FEMALE"
    OTHER = "OTHER"
    PREFER_NOT_TO_SAY = "PREFER_NOT_TO_SAY"


class SubjectProfile(PKMixin, ReprMixin, TimestampMixin, db.Model):
    """
    Subject static/low-drift indirect PII profile.

    Stores minimally identifiable attributes (e.g., sex, birth year, height).
    Enforced 1:1 relationship with :class:`Subject`.

    Fields
    ------
    subject_id : int
        FK to :class:`Subject`. Unique (1:1). ``ON DELETE CASCADE``.
    sex : SexEnum | None
        Optional. Stored as PostgreSQL enum ``enum_sex``.
    birth_year : int | None
        Optional. Year constraints enforced in validator.
    height_cm : int | None
        Optional. Must be positive if provided.
    dominant_hand : str | None
        Optional small string (e.g., "left", "right").
    """

    __tablename__ = "subject_profiles"

    # Remove unique=True here to avoid duplicate UNIQUE with __table_args__
    subject_id: Mapped[int] = mapped_column(
        ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False
    )
    sex: Mapped[SexEnum | None] = mapped_column(
        SAEnum(SexEnum, name="enum_sex", native_enum=True, create_constraint=True),
        nullable=True,
    )
    birth_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height_cm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    dominant_hand: Mapped[str | None] = mapped_column(String(10), nullable=True)

    subject = relationship("Subject", back_populates="profile", passive_deletes=True)

    __table_args__ = (
        UniqueConstraint("subject_id", name="uq_subject_profiles_subject"),
        Index("ix_subject_profiles_subject_id", "subject_id"),
        # Portable DB-level checks (SQLite/PostgreSQL).
        # Upper-bound year handled in Python validator.
        CheckConstraint(
            "(birth_year IS NULL) OR (birth_year >= 1900)",
            name="ck_subject_profiles_birth_year_range",
        ),
        CheckConstraint(
            "(height_cm IS NULL) OR (height_cm > 0)",
            name="ck_subject_profiles_height_positive",
        ),
        CheckConstraint(
            "(dominant_hand IS NULL) OR (length(dominant_hand) <= 10)",
            name="ck_subject_profiles_dominant_hand_len",
        ),
    )

    # -------------------- Validators (intercept any assignment) --------------------
    @validates("birth_year")
    def _validate_birth_year(self, key: str, value: int | None) -> int | None:
        """Validate birth year against a sane range (upper bound handled here for portability)."""
        if value is None:
            return None
        current_year = date.today().year
        if value < 1900 or value > current_year:
            raise ValueError("birth_year out of allowed range.")
        return value

    @validates("height_cm")
    def _validate_height_cm(self, key: str, value: int | None) -> int | None:
        """Ensure height is positive when present."""
        if value is None:
            return None
        if value <= 0:
            raise ValueError("height_cm must be positive.")
        return value

    @validates("dominant_hand")
    def _validate_dominant_hand(self, key: str, value: str | None) -> str | None:
        """Trim and bound dominant_hand length."""
        if value is None:
            return None
        v = value.strip()
        if not v:
            return None  # treat empty/whitespace as NULL
        if len(v) > 10:
            raise ValueError("dominant_hand must be at most 10 characters.")
        return v


class SubjectBodyMetrics(PKMixin, ReprMixin, TimestampMixin, db.Model):
    """
    Subject time-series indirect PII (body metrics).

    One row per measurement day per subject. Uniqueness is enforced on
    ``(subject_id, measured_on)``.

    Fields
    ------
    subject_id : int
        FK to :class:`Subject`. ``ON DELETE CASCADE``.
    measured_on : date
        Measurement date. Required and unique with subject_id.
    weight_kg : float | None
        Optional weight (kg). Non-negative if present.
    bodyfat_pct : float | None
        Optional body fat percentage in [0, 100].
    resting_hr : int | None
        Optional resting heart rate (bpm). Positive if present.
    notes : str | None
        Free-form notes.
    """

    __tablename__ = "subject_body_metrics"

    subject_id: Mapped[int] = mapped_column(
        ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False
    )
    measured_on: Mapped[date] = mapped_column(Date, nullable=False)

    # Use float runtime (asdecimal=False) while keeping DB NUMERIC precision.
    weight_kg: Mapped[float | None] = mapped_column(Numeric(5, 2, asdecimal=False), nullable=True)
    bodyfat_pct: Mapped[float | None] = mapped_column(Numeric(4, 1, asdecimal=False), nullable=True)
    resting_hr: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(db.Text, nullable=True)

    subject = relationship("Subject", back_populates="body_metrics", passive_deletes=True)

    __table_args__ = (
        UniqueConstraint("subject_id", "measured_on", name="uq_sbm_subject_day"),
        Index("ix_sbm_subject_id", "subject_id"),
        Index("ix_sbm_measured_on", "measured_on"),
        # DB-level checks mirroring Python validators:
        CheckConstraint(
            "(weight_kg IS NULL) OR (weight_kg >= 0)",
            name="ck_sbm_weight_nonnegative",
        ),
        CheckConstraint(
            "(bodyfat_pct IS NULL) OR (bodyfat_pct >= 0 AND bodyfat_pct <= 100)",
            name="ck_sbm_bodyfat_pct_range",
        ),
        CheckConstraint(
            "(resting_hr IS NULL) OR (resting_hr > 0)",
            name="ck_sbm_resting_hr_positive",
        ),
    )

    # -------------------- Validators (intercept any assignment) --------------------
    @validates("weight_kg")
    def _validate_weight_kg(self, key: str, value: float | None) -> float | None:
        """Ensure weight is non-negative when present."""
        if value is None:
            return None
        if value < 0:
            raise ValueError("weight_kg cannot be negative.")
        return float(value)

    @validates("bodyfat_pct")
    def _validate_bodyfat_pct(self, key: str, value: float | None) -> float | None:
        """Ensure body fat percentage is within [0, 100] when present."""
        if value is None:
            return None
        if value < 0 or value > 100:
            raise ValueError("bodyfat_pct must be within [0, 100].")
        return float(value)

    @validates("resting_hr")
    def _validate_resting_hr(self, key: str, value: int | None) -> int | None:
        """Ensure resting heart rate is positive when present."""
        if value is None:
            return None
        if value <= 0:
            raise ValueError("resting_hr must be positive.")
        return int(value)
