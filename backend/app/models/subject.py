"""Subject, SubjectProfile, and SubjectBodyMetrics models."""

from __future__ import annotations

from datetime import date
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    Date,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.extensions import db

from .base import PKMixin, ReprMixin, TimestampMixin

if TYPE_CHECKING:
    from .cycle import Cycle
    from .exercise_log import ExerciseSetLog
    from .routine import Routine
    from .workout import WorkoutSession


class Subject(PKMixin, ReprMixin, TimestampMixin, db.Model):
    """
    Pseudonymous subject entity used across the domain.

    Holds a stable pseudonymous identifier and an optional 1:1 link to ``User``.
    Breaking the link (``user_id = NULL``) supports anonymization while
    preserving domain analytics.

    Fields
    ------
    user_id : int | None
        Optional 1:1 link to :class:`app.models.user.User`. Unique when present.
    pseudonym : UUID
        Stable pseudonymous UUID (unique).
    """

    __tablename__ = "subjects"

    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, unique=True
    )
    pseudonym: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, default=uuid4)

    user = relationship(
        "User",
        uselist=False,
        backref="subject",
        passive_deletes=True,
    )

    # 1:1 profile; one-to-many body metrics
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

    # other relationships (e.g., routines)
    routines: Mapped[list[Routine]] = relationship(
        "Routine",
        back_populates="subject",
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

    subject_id: Mapped[int] = mapped_column(
        ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False, unique=True
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
    )

    # -------------------- Validators --------------------
    @staticmethod
    def _current_year() -> int:
        """Return current year as integer."""
        return date.today().year

    @property
    def _min_birth_year(self) -> int:
        """Minimum allowed birth year for sanity checks."""
        return 1900

    def set_birth_year(self, value: int | None) -> None:
        """
        Validate and set ``birth_year``.

        :param value: Year or ``None`` to unset.
        :type value: int | None
        :raises ValueError: If outside sanity range.
        """
        if value is None:
            self.birth_year = None
            return
        cy = self._current_year()
        if value < self._min_birth_year or value > cy:
            raise ValueError("birth_year out of allowed range.")
        self.birth_year = value

    def set_height_cm(self, value: int | None) -> None:
        """
        Validate and set ``height_cm``.

        :param value: Height in centimeters or ``None``.
        :type value: int | None
        :raises ValueError: If non-positive.
        """
        if value is None:
            self.height_cm = None
            return
        if value <= 0:
            raise ValueError("height_cm must be positive.")
        self.height_cm = value


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
    weight_kg : Decimal | None
        Optional weight (kg).
    bodyfat_pct : Decimal | None
        Optional body fat percentage (0..100 with one decimal as per schema).
    resting_hr : int | None
        Optional resting heart rate (bpm).
    notes : str | None
        Free-form notes.
    """

    __tablename__ = "subject_body_metrics"

    subject_id: Mapped[int] = mapped_column(
        ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False
    )
    measured_on: Mapped[date] = mapped_column(Date, nullable=False)

    weight_kg: Mapped[float | None] = mapped_column(Numeric(5, 2, asdecimal=False), nullable=True)
    bodyfat_pct: Mapped[float | None] = mapped_column(Numeric(4, 1, asdecimal=False), nullable=True)
    resting_hr: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(db.Text, nullable=True)

    subject = relationship("Subject", back_populates="body_metrics", passive_deletes=True)

    __table_args__ = (
        UniqueConstraint("subject_id", "measured_on", name="uq_sbm_subject_day"),
        Index("ix_sbm_subject_id", "subject_id"),
        Index("ix_sbm_measured_on", "measured_on"),
    )

    # -------------------- Helpers / Validations --------------------
    def set_weight_kg(self, value: float | None) -> None:
        """
        Validate and set ``weight_kg``.

        :param value: Weight in kilograms, or ``None``.
        :type value: float | None
        :raises ValueError: If negative.
        """
        if value is None:
            self.weight_kg = None
            return
        if value < 0:
            raise ValueError("weight_kg cannot be negative.")
        self.weight_kg = value

    def set_bodyfat_pct(self, value: float | None) -> None:
        """
        Validate and set ``bodyfat_pct``.

        :param value: Body fat percentage (0..100) or ``None``.
        :type value: float | None
        :raises ValueError: If outside [0, 100].
        """
        if value is None:
            self.bodyfat_pct = None
            return
        if value < 0 or value > 100:
            raise ValueError("bodyfat_pct must be within [0, 100].")
        self.bodyfat_pct = value

    def set_resting_hr(self, value: int | None) -> None:
        """
        Validate and set ``resting_hr``.

        :param value: Resting heart rate in bpm or ``None``.
        :type value: int | None
        :raises ValueError: If non-positive.
        """
        if value is None:
            self.resting_hr = None
            return
        if value <= 0:
            raise ValueError("resting_hr must be positive.")
        self.resting_hr = value
