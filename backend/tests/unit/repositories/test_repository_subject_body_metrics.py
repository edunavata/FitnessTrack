"""Unit tests for :mod:`app.repositories.subject_body_metrics`."""

from __future__ import annotations

from datetime import date

import pytest
from app.repositories import base as base_module
from app.repositories.base import Pagination
from app.repositories.subject_body_metrics import SubjectBodyMetricsRepository
from tests.factories.subject import SubjectBodyMetricsFactory, SubjectFactory


@pytest.fixture(autouse=True)
def _patch_apply_sorting(monkeypatch):
    """Provide the partial signature expected by the repository."""
    from app.repositories import subject_body_metrics as module

    def patched(stmt, tokens):
        repo = SubjectBodyMetricsRepository()
        return base_module.apply_sorting(
            stmt,
            repo._sortable_fields(),
            tokens or [],
            pk_attr=repo._pk_attr(),
        )

    monkeypatch.setattr(module, "apply_sorting", patched)


class TestSubjectBodyMetricsRepository:
    def test_list_for_subject_applies_date_bounds_and_sorting(self, session):
        subject = SubjectFactory()
        other_subject = SubjectFactory()
        repo = SubjectBodyMetricsRepository()

        within_lower = SubjectBodyMetricsFactory(
            subject=subject,
            measured_on=date(2024, 1, 5),
            weight_kg=78.5,
        )
        within_upper = SubjectBodyMetricsFactory(
            subject=subject,
            measured_on=date(2024, 1, 20),
            weight_kg=79.1,
        )
        outside_range = SubjectBodyMetricsFactory(
            subject=subject,
            measured_on=date(2023, 12, 31),
        )
        SubjectBodyMetricsFactory(
            subject=other_subject,
            measured_on=date(2024, 1, 10),
        )

        results = repo.list_for_subject(
            subject.id,
            date_from=date(2024, 1, 1),
            date_to=date(2024, 1, 31),
            sort=["-measured_on"],
        )

        assert [metric.id for metric in results] == [within_upper.id, within_lower.id]
        assert all(metric.subject_id == subject.id for metric in results)
        assert outside_range.id not in {metric.id for metric in results}

    def test_paginate_for_subject_respects_limit_and_total(self, session):
        subject = SubjectFactory()
        repo = SubjectBodyMetricsRepository()

        measurements = [
            SubjectBodyMetricsFactory(subject=subject, measured_on=date(2024, 1, day))
            for day in (1, 2, 3)
        ]

        page = repo.paginate_for_subject(
            Pagination(page=1, limit=2, sort=["measured_on"]),
            subject_id=subject.id,
            with_total=True,
        )

        assert page.page == 1
        assert page.limit == 2
        assert page.total == 3
        assert [m.id for m in page.items] == [measurements[0].id, measurements[1].id]

    def test_upsert_by_day_creates_and_updates_records(self, session):
        subject = SubjectFactory()
        repo = SubjectBodyMetricsRepository()
        measured_on = date(2024, 2, 1)

        created = repo.upsert_by_day(
            subject_id=subject.id,
            measured_on=measured_on,
            weight_kg=80.0,
            notes="initial",
        )

        assert created.id is not None
        assert created.weight_kg == pytest.approx(80.0)
        assert created.notes == "initial"

        updated = repo.upsert_by_day(
            subject_id=subject.id,
            measured_on=measured_on,
            weight_kg=79.4,
            resting_hr=52,
            notes="updated",
        )

        assert updated.id == created.id
        assert updated.weight_kg == pytest.approx(79.4)
        assert updated.resting_hr == 52
        assert updated.notes == "updated"
