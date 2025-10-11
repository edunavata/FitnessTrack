from datetime import date, timedelta

import pytest
from app.repositories.subject_body_metrics import SubjectBodyMetricsRepository
from app.services._shared.dto import PaginationIn
from app.services._shared.errors import NotFoundError, PreconditionFailedError
from app.services.subject_metrics.dto import (
    MetricsDeleteIn,
    MetricsGetIn,
    MetricsListIn,
    MetricsUpsertIn,
)
from app.services.subject_metrics.service import SubjectMetricsService
from tests.factories.subject import SubjectBodyMetricsFactory, SubjectFactory


class TestSubjectMetricsService:
    """Validate SubjectMetricsService behaviours for time-series metrics."""

    # -------------------------- Fixtures ---------------------------------- #

    @pytest.fixture()
    def service(self) -> SubjectMetricsService:
        return SubjectMetricsService()

    @pytest.fixture()
    def repo(self, session) -> SubjectBodyMetricsRepository:
        return SubjectBodyMetricsRepository(session=session)

    # -------------------------- Upsert ------------------------------------ #

    def test_upsert_inserts_new_row(self, service, repo, session):
        """Insert path: no existing row for (subject, day) → creates it."""
        s = SubjectFactory()
        session.flush()

        dto = MetricsUpsertIn(
            subject_id=s.id,
            measured_on=date(2025, 1, 10),
            weight_kg=82.3,
            bodyfat_pct=18.5,
            resting_hr=55,
            notes="Leg day.",
        )
        service.ctx.subject_id = s.id  # Simulate auth context
        out = service.upsert(dto)

        assert out.subject_id == s.id
        assert out.measured_on == date(2025, 1, 10)
        assert out.weight_kg == 82.3
        assert out.bodyfat_pct == 18.5
        assert out.resting_hr == 55
        assert out.notes == "Leg day."

        # persisted
        got = repo.find_one(subject_id=s.id, measured_on=date(2025, 1, 10))
        assert got is not None and got.weight_kg == 82.3

    def test_upsert_updates_existing_row(self, service, repo, session):
        """Update path: existing row for (subject, day) → updates fields."""
        s = SubjectFactory()
        session.flush()

        # seed existing row
        SubjectBodyMetricsFactory(subject=s, measured_on=date(2025, 2, 1), weight_kg=80.0)
        session.flush()

        dto = MetricsUpsertIn(
            subject_id=s.id,
            measured_on=date(2025, 2, 1),
            weight_kg=79.4,  # update
            bodyfat_pct=17.2,
            resting_hr=54,
            notes="Cut phase.",
        )
        service.ctx.subject_id = s.id  # Simulate auth context
        out = service.upsert(dto)

        assert out.weight_kg == 79.4
        assert out.bodyfat_pct == 17.2
        assert out.resting_hr == 54
        assert out.notes == "Cut phase."

        got = repo.find_one(subject_id=s.id, measured_on=date(2025, 2, 1))
        assert got is not None and got.weight_kg == 79.4

    def test_upsert_if_match_mismatch_raises_precondition(self, service, session):
        """If ETag is provided and current row ETag differs, raise PreconditionFailedError."""
        s = SubjectFactory()
        session.flush()

        # seed existing row
        row = SubjectBodyMetricsFactory(subject=s, measured_on=date(2025, 3, 5), weight_kg=81.0)
        session.flush()

        # Skip if model doesn't implement ETag
        if not hasattr(row, "compute_etag"):
            pytest.skip("SubjectBodyMetrics.compute_etag() not implemented; skipping ETag test.")

        bad = "bogus-etag"
        dto = MetricsUpsertIn(
            subject_id=s.id,
            measured_on=date(2025, 3, 5),
            weight_kg=80.5,
            if_match=bad,
        )
        service.ctx.subject_id = s.id  # Simulate auth context
        with pytest.raises(PreconditionFailedError):
            service.upsert(dto)

    # -------------------------- Retrieval -------------------------------- #

    def test_get_returns_row(self, service, repo, session):
        """A stored row is retrieved by unique key."""
        s = SubjectFactory()
        session.flush()
        row = SubjectBodyMetricsFactory(subject=s, measured_on=date(2025, 4, 1), weight_kg=78.9)
        session.flush()  # leave session clean for ro_uow

        service.ctx.subject_id = s.id  # Simulate auth context
        out = service.get(MetricsGetIn(subject_id=s.id, measured_on=date(2025, 4, 1)))
        assert out.id == row.id
        assert out.weight_kg == 78.9

    def test_get_not_found_raises(self, service):
        """Non-existing row raises NotFoundError."""
        SUBJECT_ID = 9999
        service.ctx.subject_id = SUBJECT_ID  # Simulate auth context
        with pytest.raises(NotFoundError):
            service.get(MetricsGetIn(subject_id=SUBJECT_ID, measured_on=date(2025, 1, 1)))

    # -------------------------- Listing ----------------------------------- #

    def test_list_with_date_range_and_sort(self, service, session):
        """List supports date range and deterministic sorting."""
        s = SubjectFactory()
        session.flush()

        d0 = date(2025, 5, 1)
        SubjectBodyMetricsFactory(subject=s, measured_on=d0 + timedelta(days=0), weight_kg=80.0)
        SubjectBodyMetricsFactory(subject=s, measured_on=d0 + timedelta(days=1), weight_kg=80.2)
        SubjectBodyMetricsFactory(subject=s, measured_on=d0 + timedelta(days=2), weight_kg=80.4)
        session.flush()  # clean before ro_uow

        dto = MetricsListIn(
            subject_id=s.id,
            pagination=PaginationIn(page=1, limit=2, sort=["-measured_on"]),
            date_from=d0,
            date_to=d0 + timedelta(days=2),
            with_total=True,
        )
        service.ctx.subject_id = s.id  # Simulate auth context
        result = service.list(dto)

        # Expect the two most recent first due to "-measured_on"
        assert len(result.items) == 2
        assert result.items[0].measured_on == d0 + timedelta(days=2)
        assert result.items[1].measured_on == d0 + timedelta(days=1)
        assert result.meta.page == 1
        assert result.meta.limit == 2
        assert result.meta.total == 3
        assert result.meta.has_next is True

    # -------------------------- Delete ------------------------------------ #

    def test_delete_idempotent_when_missing(self, service):
        """Deleting a non-existing row is idempotent (no error)."""
        SUBJECT_ID = 1234
        service.ctx.subject_id = SUBJECT_ID  # Simulate auth context
        service.delete(MetricsDeleteIn(subject_id=SUBJECT_ID, measured_on=date(2025, 6, 1)))

    def test_delete_with_if_match_mismatch(self, service, session):
        """Delete respects if_match when ETag supported."""
        s = SubjectFactory()
        session.flush()
        row = SubjectBodyMetricsFactory(subject=s, measured_on=date(2025, 6, 2))
        session.flush()
        service.ctx.subject_id = s.id  # Simulate auth context

        if not hasattr(row, "compute_etag"):
            pytest.skip("SubjectBodyMetrics.compute_etag() not implemented; skipping ETag test.")

        bad = "bogus"
        with pytest.raises(PreconditionFailedError):
            service.delete(
                MetricsDeleteIn(subject_id=s.id, measured_on=row.measured_on, if_match=bad)
            )

    # -------------------------- Model validators -------------------------- #

    def test_model_validation_weight_nonnegative(self, service, session):
        """Negative weight should raise ValueError from model validators."""
        s = SubjectFactory()
        session.flush()
        service.ctx.subject_id = s.id  # Simulate auth context

        dto = MetricsUpsertIn(subject_id=s.id, measured_on=date(2025, 7, 1), weight_kg=-1.0)
        with pytest.raises(ValueError):
            service.upsert(dto)

    def test_model_validation_bodyfat_range(self, service, session):
        """Bodyfat percent must be in [0, 100]."""
        s = SubjectFactory()
        session.flush()
        service.ctx.subject_id = s.id  # Simulate auth context
        dto = MetricsUpsertIn(subject_id=s.id, measured_on=date(2025, 7, 2), bodyfat_pct=150.0)
        with pytest.raises(ValueError):
            service.upsert(dto)

    def test_model_validation_resting_hr_positive(self, service, session):
        """Resting HR must be positive when present."""
        s = SubjectFactory()
        session.flush()
        service.ctx.subject_id = s.id  # Simulate auth context
        dto = MetricsUpsertIn(subject_id=s.id, measured_on=date(2025, 7, 3), resting_hr=0)
        with pytest.raises(ValueError):
            service.upsert(dto)
