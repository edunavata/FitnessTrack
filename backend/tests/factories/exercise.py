"""Factory Boy definitions for Exercise catalog models."""

from __future__ import annotations

from app.models.exercise import Exercise, ExerciseAlias, ExerciseTag, Tag

import factory
from tests.factories import BaseFactory


class ExerciseFactory(BaseFactory):
    """Build persisted :class:`app.models.exercise.Exercise`."""

    class Meta:
        model = Exercise

    id = None
    name = factory.Sequence(lambda n: f"Exercise {n}")
    slug = factory.Sequence(lambda n: f"exercise-{n}")

    primary_muscle = "CHEST"
    movement = "HINGE"
    mechanics = "COMPOUND"
    force = "PUSH"
    unilateral = False
    equipment = "BARBELL"
    difficulty = "BEGINNER"
    is_active = True


class ExerciseAliasFactory(BaseFactory):
    """Build persisted :class:`app.models.exercise.ExerciseAlias`."""

    class Meta:
        model = ExerciseAlias

    id = None
    exercise = factory.SubFactory(ExerciseFactory)
    alias = factory.Sequence(lambda n: f"Alias {n}")


class TagFactory(BaseFactory):
    """Build persisted :class:`app.models.exercise.Tag`."""

    class Meta:
        model = Tag

    id = None
    name = factory.Sequence(lambda n: f"Tag{n}")


class ExerciseTagFactory(BaseFactory):
    """Build persisted :class:`app.models.exercise.ExerciseTag`."""

    class Meta:
        model = ExerciseTag

    exercise = factory.SubFactory(ExerciseFactory)
    tag = factory.SubFactory(TagFactory)
