"""Exercise catalog endpoints and enumeration helpers."""

from __future__ import annotations

from http import HTTPStatus

from flask import Response, request, url_for
from sqlalchemy.exc import IntegrityError

from app.models.exercise import (
    Equipment,
    Exercise,
    ForceVector,
    Level,
    Mechanics,
    MovementPattern,
    MuscleGroup,
)

from .. import deps
from ..errors import problem
from ..etag import set_response_etag, verify_etag
from ..schemas import ExerciseCreateSchema, ExerciseSchema, ExerciseUpdateSchema
from . import api_v1

exercise_schema = ExerciseSchema()
exercise_create_schema = ExerciseCreateSchema()
exercise_update_schema = ExerciseUpdateSchema(partial=True)
exercises_schema = ExerciseSchema(many=True)

REFERENCE_ENUMS = {
    "muscle-groups": [choice for choice in MuscleGroup.enums],
    "equipment": [choice for choice in Equipment.enums],
    "mechanics": [choice for choice in Mechanics.enums],
    "force-vectors": [choice for choice in ForceVector.enums],
    "levels": [choice for choice in Level.enums],
    "movement-patterns": [choice for choice in MovementPattern.enums],
}


@api_v1.get("/exercises")
@deps.timing
def list_exercises() -> Response:
    """List exercises with filters, sorting, and pagination.

    :returns: Envelope containing serialized exercises.
    :rtype: flask.Response
    """

    # Build a catalog query and apply filter parameters.
    pagination = deps.parse_pagination()
    # Acquire a session for database work.
    session = deps.get_session()
    query = session.query(Exercise)

    name = request.args.get("name")
    primary_muscle = request.args.get("primary_muscle")
    equipment = request.args.get("equipment")
    is_active = request.args.get("is_active")

    if name:
        query = query.filter(Exercise.name.ilike(f"%{name}%"))
    if primary_muscle:
        query = query.filter(Exercise.primary_muscle == primary_muscle)
    if equipment:
        query = query.filter(Exercise.equipment == equipment)
    if is_active is not None:
        query = query.filter(Exercise.is_active == (is_active.lower() != "false"))

    sort_map = {
        "name": Exercise.name,
        "created_at": Exercise.created_at,
        "difficulty": Exercise.difficulty,
    }
    query = deps.apply_sorting(query, sort_map, pagination.sort)

    items, total = deps.paginate_query(query, pagination)
    payload = {
        "items": exercises_schema.dump(items),
        "page": pagination.page,
        "limit": pagination.limit,
        "total": total,
    }
    return deps.json_response(payload)


@api_v1.get("/exercises/<int:exercise_id>")
@deps.timing
def retrieve_exercise(exercise_id: int) -> Response:
    """Fetch exercise details.

    :param exercise_id: Exercise identifier.
    :type exercise_id: int
    :returns: Serialized exercise record with ETag header.
    :rtype: flask.Response
    """

    # Acquire a session for database work.
    session = deps.get_session()
    # Resolve the exercise or return a problem response.
    exercise = session.get(Exercise, exercise_id)
    if exercise is None:
        return problem(status=HTTPStatus.NOT_FOUND, detail="Exercise not found.", code="not_found")
    response = deps.json_response(exercise_schema.dump(exercise))
    return set_response_etag(response, exercise)


@api_v1.post("/exercises")
@deps.require_auth
@deps.require_scope("exercises:write")
@deps.timing
def create_exercise() -> Response:
    """Create an exercise entry.

    :returns: Newly created exercise resource.
    :rtype: flask.Response
    """

    # Idempotency safeguards protect against duplicate catalog entries.
    idempotency_key = request.headers.get("Idempotency-Key")
    is_replay, cached = deps.enforce_idempotency(idempotency_key)
    if is_replay and cached is not None:
        return deps.build_cached_response(cached)

    payload = request.get_json(silent=True) or {}
    data = exercise_create_schema.load(payload)

    # Acquire a session for database work.
    session = deps.get_session()
    exercise = Exercise(**data)
    session.add(exercise)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        return problem(status=HTTPStatus.CONFLICT, detail="Exercise with same slug exists.", code="conflict")

    body = exercise_schema.dump(exercise)
    response = deps.json_response(body, status=HTTPStatus.CREATED)
    set_response_etag(response, exercise)
    response.headers["Location"] = url_for("api_v1.retrieve_exercise", exercise_id=exercise.id)
    headers = {"Location": response.headers["Location"]}
    if response.headers.get("ETag"):
        headers["ETag"] = response.headers["ETag"]
    deps.store_idempotent_response(
        idempotency_key,
        {"body": body, "status": HTTPStatus.CREATED, "headers": headers},
    )
    return response


@api_v1.patch("/exercises/<int:exercise_id>")
@deps.require_auth
@deps.require_scope("exercises:write")
@deps.timing
def update_exercise(exercise_id: int) -> Response:
    """Partially update an exercise.

    :param exercise_id: Exercise identifier.
    :type exercise_id: int
    :returns: Updated exercise payload.
    :rtype: flask.Response
    """

    # Acquire a session for database work.
    session = deps.get_session()
    # Resolve the exercise or return a problem response.
    exercise = session.get(Exercise, exercise_id)
    if exercise is None:
        return problem(status=HTTPStatus.NOT_FOUND, detail="Exercise not found.", code="not_found")

    if_match = request.headers.get("If-Match")
    if not if_match:
        return problem(status=HTTPStatus.PRECONDITION_FAILED, detail="Missing If-Match header.", code="missing_if_match")
    if not verify_etag(exercise, if_match.strip('"')):
        return problem(status=HTTPStatus.PRECONDITION_FAILED, detail="ETag mismatch.", code="etag_mismatch")

    payload = request.get_json(silent=True) or {}
    # Apply partial updates only to fields provided by the client.
    data = exercise_update_schema.load(payload)
    for key, value in data.items():
        setattr(exercise, key, value)
    session.commit()
    response = deps.json_response(exercise_schema.dump(exercise))
    return set_response_etag(response, exercise)


@api_v1.delete("/exercises/<int:exercise_id>")
@deps.require_auth
@deps.require_scope("exercises:write")
@deps.timing
def delete_exercise(exercise_id: int) -> Response:
    """Soft delete an exercise by marking it inactive.

    :param exercise_id: Exercise identifier.
    :type exercise_id: int
    :returns: Updated exercise payload reflecting the inactive state.
    :rtype: flask.Response
    """

    # Acquire a session for database work.
    session = deps.get_session()
    # Resolve the exercise or return a problem response.
    exercise = session.get(Exercise, exercise_id)
    if exercise is None:
        return problem(status=HTTPStatus.NOT_FOUND, detail="Exercise not found.", code="not_found")

    if_match = request.headers.get("If-Match")
    if not if_match:
        return problem(status=HTTPStatus.PRECONDITION_FAILED, detail="Missing If-Match header.", code="missing_if_match")
    if not verify_etag(exercise, if_match.strip('"')):
        return problem(status=HTTPStatus.PRECONDITION_FAILED, detail="ETag mismatch.", code="etag_mismatch")

    exercise.is_active = False
    session.commit()
    response = deps.json_response(exercise_schema.dump(exercise))
    return set_response_etag(response, exercise)


@api_v1.get("/exercises/meta/<string:name>")
@deps.timing
def exercise_reference_data(name: str) -> Response:
    """Expose read-only exercise enumeration values.

    :param name: Enumeration name (e.g., ``muscle-groups``).
    :type name: str
    :returns: JSON payload with enumeration members or 404.
    :rtype: flask.Response
    """

    values = REFERENCE_ENUMS.get(name)
    if values is None:
        return problem(status=HTTPStatus.NOT_FOUND, detail="Enumeration not found.", code="not_found")
    payload = {"name": name, "values": values}
    return deps.json_response(payload)
