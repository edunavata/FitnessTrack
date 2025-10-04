from __future__ import annotations

import pytest
from app.repositories.exercise import ExerciseRepository
from tests.factories.exercise import ExerciseFactory


class TestExerciseSecondaryMuscles:
    @pytest.fixture()
    def repo(self) -> ExerciseRepository:
        return ExerciseRepository()

    def test_set_and_list_secondary_muscles(self, repo, session):
        ex = ExerciseFactory(name="Bench Press", slug="bench-press")
        session.add(ex)
        session.flush()

        result = repo.set_secondary_muscles(ex.id, ["TRICEPS", "FRONT_DELTS", "triceps", "  "])
        # Duplicados y espacios se limpian, upper aplicado
        assert result == ["FRONT_DELTS", "TRICEPS"]

        listed = repo.list_secondary_muscles(ex.id)
        assert set(listed) == set(result)

        # Reemplazar por un conjunto distinto
        result2 = repo.set_secondary_muscles(ex.id, ["LATS"])
        assert result2 == ["LATS"]
        assert set(repo.list_secondary_muscles(ex.id)) == {"LATS"}

    def test_add_and_remove_secondary_muscles(self, repo, session):
        ex = ExerciseFactory(name="Row", slug="row")
        session.add(ex)
        session.flush()

        # Add union
        after_add = repo.add_secondary_muscles(ex.id, ["BICEPS", "REAR_DELTS"])
        assert set(after_add) == {"BICEPS", "REAR_DELTS"}

        # Idempotente al añadir repetidos
        after_add2 = repo.add_secondary_muscles(ex.id, ["biceps"])
        assert set(after_add2) == {"BICEPS", "REAR_DELTS"}

        # Remove específicos
        removed = repo.remove_secondary_muscles(ex.id, ["BICEPS"])
        assert removed == 1
        assert set(repo.list_secondary_muscles(ex.id)) == {"REAR_DELTS"}

        # Remove all
        removed_all = repo.remove_secondary_muscles(ex.id, None)
        assert removed_all == 1
        assert repo.list_secondary_muscles(ex.id) == []

    def test_list_by_secondary_muscle(self, repo, session):
        e1 = ExerciseFactory(name="Incline Bench", slug="incline-bench")
        e2 = ExerciseFactory(name="Overhead Press", slug="ohp")
        session.add_all([e1, e2])
        session.flush()

        repo.add_secondary_muscles(e1.id, ["FRONT_DELTS"])
        repo.add_secondary_muscles(e2.id, ["FRONT_DELTS", "TRICEPS"])

        rows = repo.list_by_secondary_muscle("front_delts", sort=["name"])
        assert [x.name for x in rows] == ["Incline Bench", "Overhead Press"]
