"""Tests for Subject, SubjectProfile, and SubjectBodyMetrics."""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from app.models.subject import SexEnum, Subject, SubjectBodyMetrics, SubjectProfile
from app.models.user import User
from sqlalchemy.exc import IntegrityError


class TestSubjectProfile:
    def test_create_profile_1to1(self, session):
        # Create subject first so FK exists
        s = Subject()
        session.add(s)
        session.flush()

        # Assign fields directly; validators (@validates) must intercept
        p = SubjectProfile(subject=s, sex=SexEnum.OTHER)
        p.birth_year = 2000
        p.height_cm = 175

        session.add(p)
        session.commit()

        assert p.subject_id == s.id
        assert p.sex == SexEnum.OTHER
        assert p.birth_year == 2000
        assert p.height_cm == 175
        assert s.profile.id == p.id  # 1:1 backref linkage

    def test_profile_unique_per_subject(self, session):
        s = Subject()
        session.add(s)
        session.flush()

        p1 = SubjectProfile(subject=s)
        session.add(p1)
        session.commit()

        p2 = SubjectProfile(subject=s)
        session.add(p2)
        with pytest.raises(IntegrityError):
            session.commit()

    def test_profile_delete_cascades_with_subject(self, session):
        if session.bind.dialect.name == "sqlite":
            pytest.skip("SQLite FK ON DELETE may be disabled in test env.")

        u = User(email="x@example.com", username="x")
        u.password = "pw"
        s = Subject(user=u)
        p = SubjectProfile(subject=s, sex=SexEnum.MALE)

        session.add_all([u, s, p])
        session.commit()

        session.delete(s)
        session.commit()

        assert session.get(SubjectProfile, p.id) is None

    def test_validators_birth_year_and_height(self, session):
        s = Subject()
        p = SubjectProfile(subject=s)

        # Invalid birth_year (too small)
        with pytest.raises(ValueError):
            p.birth_year = 1800

        # Invalid birth_year (future)
        with pytest.raises(ValueError):
            p.birth_year = date.today().year + 1

        # None is allowed (unset)
        p.birth_year = None
        assert p.birth_year is None

        # Non-positive height is invalid
        with pytest.raises(ValueError):
            p.height_cm = 0

        # None is allowed (unset)
        p.height_cm = None
        assert p.height_cm is None


class TestSubjectBodyMetrics:
    def test_unique_measurement_per_day(self, session):
        s = Subject()
        session.add(s)
        session.flush()

        m1 = SubjectBodyMetrics(subject=s, measured_on=date.today(), weight_kg=80.0)
        session.add(m1)
        session.commit()

        m2 = SubjectBodyMetrics(subject=s, measured_on=date.today(), weight_kg=81.0)
        session.add(m2)
        with pytest.raises(IntegrityError):
            session.commit()

    def test_metrics_delete_cascades_with_subject(self, session):
        if session.bind.dialect.name == "sqlite":
            pytest.skip("SQLite FK ON DELETE may be disabled in test env.")

        s = Subject()
        m = SubjectBodyMetrics(subject=s, measured_on=date.today(), weight_kg=79.0)
        session.add_all([s, m])
        session.commit()

        session.delete(s)
        session.commit()

        assert session.get(SubjectBodyMetrics, m.id) is None

    def test_validators_on_assignment(self, session):
        # Assignments must trigger @validates and raise when invalid
        s = Subject()
        m = SubjectBodyMetrics(subject=s, measured_on=date.today())

        with pytest.raises(ValueError):
            m.weight_kg = -1

        with pytest.raises(ValueError):
            m.bodyfat_pct = -0.1

        with pytest.raises(ValueError):
            m.bodyfat_pct = 100.1

        with pytest.raises(ValueError):
            m.resting_hr = 0

        # Valid values
        m.weight_kg = 82.3
        m.bodyfat_pct = 12.5
        m.resting_hr = 55

        session.add_all([s, m])
        session.commit()

        # Use approx for floats (more robust cross-dialect)
        assert m.weight_kg == pytest.approx(82.3)
        assert m.bodyfat_pct == pytest.approx(12.5)
        assert m.resting_hr == 55

    def test_multiple_days_ok(self, session):
        s = Subject()
        session.add(s)
        session.flush()

        d1 = date.today()
        d2 = d1 - timedelta(days=1)

        m1 = SubjectBodyMetrics(subject=s, measured_on=d1, weight_kg=80.0)
        m2 = SubjectBodyMetrics(subject=s, measured_on=d2, weight_kg=79.3)

        session.add_all([m1, m2])
        session.commit()

        assert {m1.measured_on, m2.measured_on} == {d1, d2}
