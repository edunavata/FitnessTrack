"""Workout session and exercise log endpoints."""

from __future__ import annotations

from datetime import datetime
from http import HTTPStatus

from flask import Response, request, url_for

from app.models.exercise_log import ExerciseSetLog
from app.models.workout import WorkoutSession

from .. import deps
from ..errors import problem
from ..etag import set_response_etag, verify_etag
from ..schemas import ExerciseSetLogSchema, ExerciseSetLogUpdateSchema, WorkoutSessionSchema, WorkoutSessionUpdateSchema
from . import api_v1

session_schema = WorkoutSessionSchema()
sessions_schema = WorkoutSessionSchema(many=True)
session_update_schema = WorkoutSessionUpdateSchema(partial=True)
log_schema = ExerciseSetLogSchema()
logs_schema = ExerciseSetLogSchema(many=True)
log_update_schema = ExerciseSetLogUpdateSchema(partial=True)


def _parse_datetime(value: str | None) -> datetime | None:
    """Parse ISO 8601 timestamps returning ``None`` when parsing fails."""

    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


@api_v1.get("/workouts/sessions")
@deps.timing
def list_sessions() -> Response:
    """List workout sessions with optional filters."""

    pagination = deps.parse_pagination()
    # Acquire a session for database work.
    session = deps.get_session()
    query = session.query(WorkoutSession)

    subject_id = request.args.get("subject_id", type=int)
    status = request.args.get("status")
    start_at = _parse_datetime(request.args.get("from"))
    end_at = _parse_datetime(request.args.get("to"))

    if subject_id is not None:
        query = query.filter(WorkoutSession.subject_id == subject_id)
    if status:
        query = query.filter(WorkoutSession.status == status)
    if start_at:
        query = query.filter(WorkoutSession.workout_date >= start_at)
    if end_at:
        query = query.filter(WorkoutSession.workout_date <= end_at)

    sort_map = {"workout_date": WorkoutSession.workout_date, "created_at": WorkoutSession.created_at}
    query = deps.apply_sorting(query, sort_map, pagination.sort)

    items, total = deps.paginate_query(query, pagination)
    payload = {
        "items": sessions_schema.dump(items),
        "page": pagination.page,
        "limit": pagination.limit,
        "total": total,
    }
    return deps.json_response(payload)


@api_v1.get("/workouts/sessions/<int:session_id>")
@deps.timing
def retrieve_session(session_id: int) -> Response:
    """Retrieve a workout session."""

    # Acquire a session for database work.
    session = deps.get_session()
    workout = session.get(WorkoutSession, session_id)
    if workout is None:
        return problem(status=HTTPStatus.NOT_FOUND, detail="Workout session not found.", code="not_found")
    response = deps.json_response(session_schema.dump(workout))
    return set_response_etag(response, workout)


@api_v1.post("/workouts/sessions")
@deps.require_auth
@deps.require_scope("workouts:write")
@deps.timing
def create_session() -> Response:
    """Create a workout session."""

    idempotency_key = request.headers.get("Idempotency-Key")
    is_replay, cached = deps.enforce_idempotency(idempotency_key)
    if is_replay and cached is not None:
        return deps.build_cached_response(cached)

    payload = request.get_json(silent=True) or {}
    data = session_schema.load(payload)

    # Acquire a session for database work.
    session = deps.get_session()
    workout = WorkoutSession(**data)
    session.add(workout)
    session.commit()

    body = session_schema.dump(workout)
    response = deps.json_response(body, status=HTTPStatus.CREATED)
    set_response_etag(response, workout)
    response.headers["Location"] = url_for("api_v1.retrieve_session", session_id=workout.id)
    headers = {"Location": response.headers["Location"]}
    if response.headers.get("ETag"):
        headers["ETag"] = response.headers["ETag"]
    deps.store_idempotent_response(
        idempotency_key,
        {"body": body, "status": HTTPStatus.CREATED, "headers": headers},
    )
    return response


@api_v1.patch("/workouts/sessions/<int:session_id>")
@deps.require_auth
@deps.require_scope("workouts:write")
@deps.timing
def update_session(session_id: int) -> Response:
    """Patch a workout session."""

    # Acquire a session for database work.
    session = deps.get_session()
    workout = session.get(WorkoutSession, session_id)
    if workout is None:
        return problem(status=HTTPStatus.NOT_FOUND, detail="Workout session not found.", code="not_found")

    if_match = request.headers.get("If-Match")
    if not if_match:
        return problem(status=HTTPStatus.PRECONDITION_FAILED, detail="Missing If-Match header.", code="missing_if_match")
    if not verify_etag(workout, if_match.strip('"')):
        return problem(status=HTTPStatus.PRECONDITION_FAILED, detail="ETag mismatch.", code="etag_mismatch")

    payload = request.get_json(silent=True) or {}
    data = session_update_schema.load(payload)
    for key, value in data.items():
        setattr(workout, key, value)
    session.commit()
    response = deps.json_response(session_schema.dump(workout))
    return set_response_etag(response, workout)


@api_v1.delete("/workouts/sessions/<int:session_id>")
@deps.require_auth
@deps.require_scope("workouts:write")
@deps.timing
def delete_session(session_id: int) -> Response:
    """Delete a workout session."""

    # Acquire a session for database work.
    session = deps.get_session()
    workout = session.get(WorkoutSession, session_id)
    if workout is None:
        return problem(status=HTTPStatus.NOT_FOUND, detail="Workout session not found.", code="not_found")

    if_match = request.headers.get("If-Match")
    if not if_match:
        return problem(status=HTTPStatus.PRECONDITION_FAILED, detail="Missing If-Match header.", code="missing_if_match")
    if not verify_etag(workout, if_match.strip('"')):
        return problem(status=HTTPStatus.PRECONDITION_FAILED, detail="ETag mismatch.", code="etag_mismatch")

    session.delete(workout)
    session.commit()
    return Response(status=HTTPStatus.NO_CONTENT)


@api_v1.get("/workouts/set-logs")
@deps.timing
def list_logs() -> Response:
    """List exercise set logs filtered by subject, exercise, or session."""

    pagination = deps.parse_pagination()
    # Acquire a session for database work.
    session = deps.get_session()
    query = session.query(ExerciseSetLog)

    subject_id = request.args.get("subject_id", type=int)
    exercise_id = request.args.get("exercise_id", type=int)
    session_id = request.args.get("session_id", type=int)
    start_at = _parse_datetime(request.args.get("from"))
    end_at = _parse_datetime(request.args.get("to"))

    if subject_id is not None:
        query = query.filter(ExerciseSetLog.subject_id == subject_id)
    if exercise_id is not None:
        query = query.filter(ExerciseSetLog.exercise_id == exercise_id)
    if session_id is not None:
        query = query.filter(ExerciseSetLog.session_id == session_id)
    if start_at:
        query = query.filter(ExerciseSetLog.performed_at >= start_at)
    if end_at:
        query = query.filter(ExerciseSetLog.performed_at <= end_at)

    sort_map = {"performed_at": ExerciseSetLog.performed_at, "created_at": ExerciseSetLog.created_at}
    query = deps.apply_sorting(query, sort_map, pagination.sort)

    items, total = deps.paginate_query(query, pagination)
    payload = {
        "items": logs_schema.dump(items),
        "page": pagination.page,
        "limit": pagination.limit,
        "total": total,
    }
    return deps.json_response(payload)


@api_v1.get("/workouts/set-logs/<int:log_id>")
@deps.timing
def retrieve_log(log_id: int) -> Response:
    """Retrieve a single exercise set log."""

    # Acquire a session for database work.
    session = deps.get_session()
    log = session.get(ExerciseSetLog, log_id)
    if log is None:
        return problem(status=HTTPStatus.NOT_FOUND, detail="Exercise set log not found.", code="not_found")
    response = deps.json_response(log_schema.dump(log))
    return set_response_etag(response, log)


@api_v1.post("/workouts/set-logs")
@deps.require_auth
@deps.require_scope("workouts:write")
@deps.timing
def create_log() -> Response:
    """Create an exercise set log."""

    idempotency_key = request.headers.get("Idempotency-Key")
    is_replay, cached = deps.enforce_idempotency(idempotency_key)
    if is_replay and cached is not None:
        return deps.build_cached_response(cached)

    payload = request.get_json(silent=True) or {}
    data = log_schema.load(payload)

    # Acquire a session for database work.
    session = deps.get_session()
    log = ExerciseSetLog(**data)
    session.add(log)
    session.commit()

    body = log_schema.dump(log)
    response = deps.json_response(body, status=HTTPStatus.CREATED)
    set_response_etag(response, log)
    response.headers["Location"] = url_for("api_v1.retrieve_log", log_id=log.id)
    headers = {"Location": response.headers["Location"]}
    if response.headers.get("ETag"):
        headers["ETag"] = response.headers["ETag"]
    deps.store_idempotent_response(
        idempotency_key,
        {"body": body, "status": HTTPStatus.CREATED, "headers": headers},
    )
    return response


@api_v1.patch("/workouts/set-logs/<int:log_id>")
@deps.require_auth
@deps.require_scope("workouts:write")
@deps.timing
def update_log(log_id: int) -> Response:
    """Patch an exercise set log."""

    # Acquire a session for database work.
    session = deps.get_session()
    log = session.get(ExerciseSetLog, log_id)
    if log is None:
        return problem(status=HTTPStatus.NOT_FOUND, detail="Exercise set log not found.", code="not_found")

    if_match = request.headers.get("If-Match")
    if not if_match:
        return problem(status=HTTPStatus.PRECONDITION_FAILED, detail="Missing If-Match header.", code="missing_if_match")
    if not verify_etag(log, if_match.strip('"')):
        return problem(status=HTTPStatus.PRECONDITION_FAILED, detail="ETag mismatch.", code="etag_mismatch")

    payload = request.get_json(silent=True) or {}
    data = log_update_schema.load(payload)
    for key, value in data.items():
        setattr(log, key, value)
    session.commit()
    response = deps.json_response(log_schema.dump(log))
    return set_response_etag(response, log)


@api_v1.delete("/workouts/set-logs/<int:log_id>")
@deps.require_auth
@deps.require_scope("workouts:write")
@deps.timing
def delete_log(log_id: int) -> Response:
    """Delete an exercise set log."""

    # Acquire a session for database work.
    session = deps.get_session()
    log = session.get(ExerciseSetLog, log_id)
    if log is None:
        return problem(status=HTTPStatus.NOT_FOUND, detail="Exercise set log not found.", code="not_found")

    if_match = request.headers.get("If-Match")
    if not if_match:
        return problem(status=HTTPStatus.PRECONDITION_FAILED, detail="Missing If-Match header.", code="missing_if_match")
    if not verify_etag(log, if_match.strip('"')):
        return problem(status=HTTPStatus.PRECONDITION_FAILED, detail="ETag mismatch.", code="etag_mismatch")

    session.delete(log)
    session.commit()
    return Response(status=HTTPStatus.NO_CONTENT)
