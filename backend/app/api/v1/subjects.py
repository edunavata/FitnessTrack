"""Subject resource endpoints including profiles and metrics."""

from __future__ import annotations

from http import HTTPStatus
from datetime import date

from flask import Response, request, url_for

from app.models.subject import Subject, SubjectBodyMetrics, SubjectProfile

from .. import deps
from ..errors import problem
from ..etag import set_response_etag, verify_etag
from ..schemas import (
    BodyMetricSchema,
    SubjectCreateSchema,
    SubjectProfileSchema,
    SubjectSchema,
    SubjectUpdateSchema,
)
from . import api_v1

subject_schema = SubjectSchema()
subjects_schema = SubjectSchema(many=True)
subject_create_schema = SubjectCreateSchema()
subject_update_schema = SubjectUpdateSchema(partial=True)
profile_schema = SubjectProfileSchema()
body_metric_schema = BodyMetricSchema()
body_metrics_schema = BodyMetricSchema(many=True)
body_metric_update_schema = BodyMetricSchema(partial=True)


@api_v1.get("/subjects")
@deps.timing
def list_subjects() -> Response:
    """Return a paginated list of subjects.

    :returns: JSON response containing the standard pagination envelope.
    :rtype: flask.Response
    """

    # Build the base query and honor query-string filters.
    pagination = deps.parse_pagination()
    # Acquire a session for database work.
    session = deps.get_session()
    query = session.query(Subject)

    user_id = request.args.get("user_id", type=int)
    pseudonym = request.args.get("pseudonym")
    if user_id is not None:
        query = query.filter(Subject.user_id == user_id)
    if pseudonym:
        query = query.filter(Subject.pseudonym == pseudonym)

    sort_map = {"id": Subject.id, "created_at": Subject.created_at}
    query = deps.apply_sorting(query, sort_map, pagination.sort)

    items, total = deps.paginate_query(query, pagination)
    payload = {
        "items": subjects_schema.dump(items),
        "page": pagination.page,
        "limit": pagination.limit,
        "total": total,
    }
    return deps.json_response(payload)


@api_v1.get("/subjects/<int:subject_id>")
@deps.timing
def retrieve_subject(subject_id: int) -> Response:
    """Retrieve a subject by identifier.

    :param subject_id: Subject primary key.
    :type subject_id: int
    :returns: Serialized subject payload with ETag header.
    :rtype: flask.Response
    """

    # Acquire a session for database work.
    session = deps.get_session()
    # Resolve the subject or respond with a Problem document.
    subject = session.get(Subject, subject_id)
    if subject is None:
        return problem(status=HTTPStatus.NOT_FOUND, detail="Subject not found.", code="not_found")
    response = deps.json_response(subject_schema.dump(subject))
    return set_response_etag(response, subject)


@api_v1.post("/subjects")
@deps.require_auth
@deps.require_scope("subjects:write")
@deps.timing
def create_subject() -> Response:
    """Create a new subject entity.

    :returns: Serialized subject payload with ``201 Created``.
    :rtype: flask.Response
    """

    # Enforce idempotency before any database writes.
    idempotency_key = request.headers.get("Idempotency-Key")
    is_replay, cached = deps.enforce_idempotency(idempotency_key)
    if is_replay and cached is not None:
        return deps.build_cached_response(cached)

    payload = request.get_json(silent=True) or {}
    data = subject_create_schema.load(payload)

    # Acquire a session for database work.
    session = deps.get_session()
    subject = Subject(user_id=data.get("user_id"))
    session.add(subject)
    session.commit()

    body = subject_schema.dump(subject)
    response = deps.json_response(body, status=HTTPStatus.CREATED)
    set_response_etag(response, subject)
    response.headers["Location"] = url_for("api_v1.retrieve_subject", subject_id=subject.id)
    headers = {"Location": response.headers["Location"]}
    if response.headers.get("ETag"):
        headers["ETag"] = response.headers["ETag"]
    deps.store_idempotent_response(
        idempotency_key,
        {"body": body, "status": HTTPStatus.CREATED, "headers": headers},
    )
    return response


@api_v1.patch("/subjects/<int:subject_id>")
@deps.require_auth
@deps.require_scope("subjects:write")
@deps.timing
def update_subject(subject_id: int) -> Response:
    """Partially update a subject.

    :param subject_id: Subject identifier to mutate.
    :type subject_id: int
    :returns: Updated subject representation.
    :rtype: flask.Response
    """

    # Acquire a session for database work.
    session = deps.get_session()
    # Resolve the subject or respond with a Problem document.
    subject = session.get(Subject, subject_id)
    if subject is None:
        return problem(status=HTTPStatus.NOT_FOUND, detail="Subject not found.", code="not_found")

    # Require clients to present the latest ETag.
    if_match = request.headers.get("If-Match")
    if not if_match:
        return problem(status=HTTPStatus.PRECONDITION_FAILED, detail="Missing If-Match header.", code="missing_if_match")
    if not verify_etag(subject, if_match.strip('"')):
        return problem(status=HTTPStatus.PRECONDITION_FAILED, detail="ETag mismatch.", code="etag_mismatch")

    payload = request.get_json(silent=True) or {}
    data = subject_update_schema.load(payload)

    if "user_id" in data:
        subject.user_id = data["user_id"]

    session.commit()
    response = deps.json_response(subject_schema.dump(subject))
    return set_response_etag(response, subject)


@api_v1.delete("/subjects/<int:subject_id>")
@deps.require_auth
@deps.require_scope("subjects:write")
@deps.timing
def delete_subject(subject_id: int) -> Response:
    """Delete a subject and cascading domain data.

    :param subject_id: Subject identifier to delete.
    :type subject_id: int
    :returns: Empty ``204 No Content`` response when deletion succeeds.
    :rtype: flask.Response
    """

    # Acquire a session for database work.
    session = deps.get_session()
    # Resolve the subject or respond with a Problem document.
    subject = session.get(Subject, subject_id)
    if subject is None:
        return problem(status=HTTPStatus.NOT_FOUND, detail="Subject not found.", code="not_found")

    # Require clients to present the latest ETag.
    if_match = request.headers.get("If-Match")
    if not if_match:
        return problem(status=HTTPStatus.PRECONDITION_FAILED, detail="Missing If-Match header.", code="missing_if_match")
    if not verify_etag(subject, if_match.strip('"')):
        return problem(status=HTTPStatus.PRECONDITION_FAILED, detail="ETag mismatch.", code="etag_mismatch")

    session.delete(subject)
    session.commit()
    return Response(status=HTTPStatus.NO_CONTENT)


@api_v1.get("/subjects/<int:subject_id>/profile")
@deps.timing
def get_subject_profile(subject_id: int) -> Response:
    """Return a subject profile document.

    :param subject_id: Parent subject identifier.
    :type subject_id: int
    :returns: Profile payload or 404 when missing.
    :rtype: flask.Response
    """

    # Acquire a session for database work.
    session = deps.get_session()
    # Resolve the subject or respond with a Problem document.
    subject = session.get(Subject, subject_id)
    if subject is None:
        return problem(status=HTTPStatus.NOT_FOUND, detail="Subject not found.", code="not_found")
    # Reuse the relationship to access or build the profile.
    profile = subject.profile
    if profile is None:
        return problem(status=HTTPStatus.NOT_FOUND, detail="Profile not found.", code="not_found")
    response = deps.json_response(profile_schema.dump(profile))
    return set_response_etag(response, profile)


@api_v1.put("/subjects/<int:subject_id>/profile")
@deps.require_auth
@deps.require_scope("subjects:write")
@deps.timing
def upsert_subject_profile(subject_id: int) -> Response:
    """Create or replace a subject profile.

    Existing profiles require ``If-Match`` to avoid lost updates.

    :param subject_id: Parent subject identifier.
    :type subject_id: int
    :returns: Updated or created profile representation.
    :rtype: flask.Response
    """

    payload = request.get_json(silent=True) or {}
    data = profile_schema.load(payload)

    # Acquire a session for database work.
    session = deps.get_session()
    # Resolve the subject or respond with a Problem document.
    subject = session.get(Subject, subject_id)
    if subject is None:
        return problem(status=HTTPStatus.NOT_FOUND, detail="Subject not found.", code="not_found")

    # Reuse the relationship to access or build the profile.
    profile = subject.profile
    if profile is None:
        profile = SubjectProfile(subject_id=subject.id)
        session.add(profile)
    else:
        # Require clients to present the latest ETag.
        if_match = request.headers.get("If-Match")
        if not if_match:
            return problem(status=HTTPStatus.PRECONDITION_FAILED, detail="Missing If-Match header.", code="missing_if_match")
        if not verify_etag(profile, if_match.strip('"')):
            return problem(status=HTTPStatus.PRECONDITION_FAILED, detail="ETag mismatch.", code="etag_mismatch")

    for key, value in data.items():
        if key != "id":
            setattr(profile, key, value)

    session.commit()
    response = deps.json_response(profile_schema.dump(profile))
    return set_response_etag(response, profile)


@api_v1.get("/subjects/<int:subject_id>/body-metrics")
@deps.timing
def list_body_metrics(subject_id: int) -> Response:
    """List body metrics for a subject.

    :param subject_id: Parent subject identifier.
    :type subject_id: int
    :returns: Paginated envelope of measurements.
    :rtype: flask.Response
    """

    # Acquire a session for database work.
    session = deps.get_session()
    # Resolve the subject or respond with a Problem document.
    subject = session.get(Subject, subject_id)
    if subject is None:
        return problem(status=HTTPStatus.NOT_FOUND, detail="Subject not found.", code="not_found")

    # Build the base query and honor query-string filters.
    pagination = deps.parse_pagination()
    # Scope the metrics query to the parent subject.
    query = session.query(SubjectBodyMetrics).filter(SubjectBodyMetrics.subject_id == subject.id)

    measured_on = request.args.get("measured_on")
    if measured_on:
        try:
            measured_date = date.fromisoformat(measured_on)
        except ValueError:
            return problem(status=HTTPStatus.BAD_REQUEST, detail="Invalid measured_on date format.", code="invalid_date")
        query = query.filter(SubjectBodyMetrics.measured_on == measured_date)

    sort_map = {"measured_on": SubjectBodyMetrics.measured_on, "created_at": SubjectBodyMetrics.created_at}
    query = deps.apply_sorting(query, sort_map, pagination.sort)

    items, total = deps.paginate_query(query, pagination)
    payload = {
        "items": body_metrics_schema.dump(items),
        "page": pagination.page,
        "limit": pagination.limit,
        "total": total,
    }
    return deps.json_response(payload)


@api_v1.post("/subjects/<int:subject_id>/body-metrics")
@deps.require_auth
@deps.require_scope("subjects:write")
@deps.timing
def create_body_metric(subject_id: int) -> Response:
    """Create a body metric entry for a subject.

    :param subject_id: Parent subject identifier.
    :type subject_id: int
    :returns: Created metric document.
    :rtype: flask.Response
    """

    # Enforce idempotency before any database writes.
    idempotency_key = request.headers.get("Idempotency-Key")
    is_replay, cached = deps.enforce_idempotency(idempotency_key)
    if is_replay and cached is not None:
        return deps.build_cached_response(cached)

    payload = request.get_json(silent=True) or {}
    data = body_metric_schema.load(payload)

    # Acquire a session for database work.
    session = deps.get_session()
    # Resolve the subject or respond with a Problem document.
    subject = session.get(Subject, subject_id)
    if subject is None:
        return problem(status=HTTPStatus.NOT_FOUND, detail="Subject not found.", code="not_found")

    metric = SubjectBodyMetrics(subject_id=subject.id, **data)
    session.add(metric)
    session.commit()

    body = body_metric_schema.dump(metric)
    response = deps.json_response(body, status=HTTPStatus.CREATED)
    set_response_etag(response, metric)
    response.headers["Location"] = url_for(
        "api_v1.get_body_metric", subject_id=subject.id, metric_id=metric.id
    )
    headers = {"Location": response.headers["Location"]}
    if response.headers.get("ETag"):
        headers["ETag"] = response.headers["ETag"]
    deps.store_idempotent_response(
        idempotency_key,
        {"body": body, "status": HTTPStatus.CREATED, "headers": headers},
    )
    return response


@api_v1.get("/subjects/<int:subject_id>/body-metrics/<int:metric_id>")
@deps.timing
def get_body_metric(subject_id: int, metric_id: int) -> Response:
    """Retrieve a single body metric entry.

    :param subject_id: Parent subject identifier.
    :type subject_id: int
    :param metric_id: Metric identifier.
    :type metric_id: int
    :returns: Serialized metric payload.
    :rtype: flask.Response
    """

    # Acquire a session for database work.
    session = deps.get_session()
    # Locate the metric within the parent subject namespace.
    metric = (
        session.query(SubjectBodyMetrics)
        .filter(SubjectBodyMetrics.subject_id == subject_id, SubjectBodyMetrics.id == metric_id)
        .first()
    )
    if metric is None:
        return problem(status=HTTPStatus.NOT_FOUND, detail="Metric not found.", code="not_found")
    response = deps.json_response(body_metric_schema.dump(metric))
    return set_response_etag(response, metric)


@api_v1.patch("/subjects/<int:subject_id>/body-metrics/<int:metric_id>")
@deps.require_auth
@deps.require_scope("subjects:write")
@deps.timing
def update_body_metric(subject_id: int, metric_id: int) -> Response:
    """Patch a body metric entry.

    :param subject_id: Parent subject identifier.
    :type subject_id: int
    :param metric_id: Metric identifier.
    :type metric_id: int
    :returns: Updated metric representation.
    :rtype: flask.Response
    """

    # Acquire a session for database work.
    session = deps.get_session()
    # Locate the metric within the parent subject namespace.
    metric = (
        session.query(SubjectBodyMetrics)
        .filter(SubjectBodyMetrics.subject_id == subject_id, SubjectBodyMetrics.id == metric_id)
        .first()
    )
    if metric is None:
        return problem(status=HTTPStatus.NOT_FOUND, detail="Metric not found.", code="not_found")

    # Require clients to present the latest ETag.
    if_match = request.headers.get("If-Match")
    if not if_match:
        return problem(status=HTTPStatus.PRECONDITION_FAILED, detail="Missing If-Match header.", code="missing_if_match")
    if not verify_etag(metric, if_match.strip('"')):
        return problem(status=HTTPStatus.PRECONDITION_FAILED, detail="ETag mismatch.", code="etag_mismatch")

    payload = request.get_json(silent=True) or {}
    data = body_metric_update_schema.load(payload)

    for key, value in data.items():
        setattr(metric, key, value)

    session.commit()
    response = deps.json_response(body_metric_schema.dump(metric))
    return set_response_etag(response, metric)


@api_v1.delete("/subjects/<int:subject_id>/body-metrics/<int:metric_id>")
@deps.require_auth
@deps.require_scope("subjects:write")
@deps.timing
def delete_body_metric(subject_id: int, metric_id: int) -> Response:
    """Delete a body metric entry.

    :param subject_id: Parent subject identifier.
    :type subject_id: int
    :param metric_id: Metric identifier.
    :type metric_id: int
    :returns: Empty ``204 No Content`` response.
    :rtype: flask.Response
    """

    # Acquire a session for database work.
    session = deps.get_session()
    # Locate the metric within the parent subject namespace.
    metric = (
        session.query(SubjectBodyMetrics)
        .filter(SubjectBodyMetrics.subject_id == subject_id, SubjectBodyMetrics.id == metric_id)
        .first()
    )
    if metric is None:
        return problem(status=HTTPStatus.NOT_FOUND, detail="Metric not found.", code="not_found")

    # Require clients to present the latest ETag.
    if_match = request.headers.get("If-Match")
    if not if_match:
        return problem(status=HTTPStatus.PRECONDITION_FAILED, detail="Missing If-Match header.", code="missing_if_match")
    if not verify_etag(metric, if_match.strip('"')):
        return problem(status=HTTPStatus.PRECONDITION_FAILED, detail="ETag mismatch.", code="etag_mismatch")

    session.delete(metric)
    session.commit()
    return Response(status=HTTPStatus.NO_CONTENT)
