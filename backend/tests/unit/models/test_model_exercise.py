"""Unit tests for Exercise catalog models."""

from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError
from tests.factories.exercise import (
    ExerciseAliasFactory,
    ExerciseFactory,
    ExerciseTagFactory,
    TagFactory,
)


class TestExerciseModel:
    def test_basic_persistence(self, session):
        ex = ExerciseFactory()
        session.add(ex)
        session.commit()

        assert ex.id is not None
        assert ex.slug.startswith("exercise-")
        assert ex.is_active is True

    def test_unique_slug_constraint(self, session):
        e1 = ExerciseFactory(slug="bench-press")
        session.add(e1)
        session.commit()

        # build (no persistido aún)
        e2 = ExerciseFactory.build(slug="bench-press")
        session.add(e2)

        with pytest.raises(IntegrityError):
            session.flush()  # aquí forzamos el error
        session.rollback()

    def test_alias_uniqueness(self, session):
        ex = ExerciseFactory()
        session.add(ex)
        session.commit()

        alias1 = ExerciseAliasFactory(exercise=ex, alias="Hip Thrust")
        alias2 = ExerciseAliasFactory.build(exercise=ex, alias="Hip Thrust")

        session.add(alias1)
        session.add(alias2)
        with pytest.raises(IntegrityError):
            session.commit()

    def test_tag_uniqueness(self, session):
        ex = ExerciseFactory()
        tag = TagFactory(name="POWERLIFTING")
        session.add_all([ex, tag])
        session.commit()

        et1 = ExerciseTagFactory(exercise=ex, tag=tag)
        session.add(et1)
        session.commit()

        et2 = ExerciseTagFactory.build(exercise=ex, tag=tag)
        session.add(et2)
        with pytest.raises(IntegrityError):
            session.commit()

    def test_relationships_navigation(self, session):
        ex = ExerciseFactory()
        alias = ExerciseAliasFactory(exercise=ex)
        tag = TagFactory()
        et = ExerciseTagFactory(exercise=ex, tag=tag)

        session.add_all([ex, alias, tag, et])
        session.commit()

        assert alias in ex.aliases
        assert et in ex.tags
        assert et.exercise == ex
        assert et.tag == tag
        assert et in tag.exercises
