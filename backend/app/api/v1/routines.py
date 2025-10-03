"""Routine template endpoints including nested hierarchy management."""

from __future__ import annotations

from http import HTTPStatus

from flask import Response, request, url_for

from app.models.routine import (
    Routine,
    RoutineDay,
    RoutineDayExercise,
    RoutineExerciseSet,
)

from .. import deps
from ..errors import problem
from ..etag import set_response_etag, verify_etag
from ..schemas import (
    RoutineCreateSchema,
    RoutineDayExerciseSchema,
    RoutineDayExerciseUpdateSchema,
    RoutineDaySchema,
    RoutineDayUpdateSchema,
    RoutineExerciseSetSchema,
    RoutineExerciseSetUpdateSchema,
    RoutineSchema,
    RoutineUpdateSchema,
)
from . import api_v1

routine_schema = RoutineSchema()
routines_schema = RoutineSchema(many=True)
routine_create_schema = RoutineCreateSchema()
routine_update_schema = RoutineUpdateSchema(partial=True)
routine_day_schema = RoutineDaySchema()
routine_days_schema = RoutineDaySchema(many=True)
routine_day_update_schema = RoutineDayUpdateSchema(partial=True)
routine_day_exercise_schema = RoutineDayExerciseSchema()
routine_day_exercises_schema = RoutineDayExerciseSchema(many=True)
routine_day_exercise_update_schema = RoutineDayExerciseUpdateSchema(partial=True)
routine_set_schema = RoutineExerciseSetSchema()
routine_sets_schema = RoutineExerciseSetSchema(many=True)
routine_set_update_schema = RoutineExerciseSetUpdateSchema(partial=True)


@api_v1.get("/routines")
@deps.timing
def list_routines() -> Response:
    """Return paginated routines filtered by owner or name.

    :returns: Standard pagination envelope with routine data.
    :rtype: flask.Response
    """

    pagination = deps.parse_pagination()
    # Acquire a session for database work.
    session = deps.get_session()
    query = session.query(Routine)

    owner_subject_id = request.args.get("owner_subject_id", type=int)
    name = request.args.get("name")
    is_public = request.args.get("is_public")

    if owner_subject_id is not None:
        query = query.filter(Routine.owner_subject_id == owner_subject_id)
    if name:
        query = query.filter(Routine.name.ilike(f"%{name}%"))
    if is_public is not None:
        query = query.filter(Routine.is_public == (is_public.lower() != "false"))

    sort_map = {"created_at": Routine.created_at, "name": Routine.name}
    query = deps.apply_sorting(query, sort_map, pagination.sort)

    items, total = deps.paginate_query(query, pagination)
    payload = {
        "items": routines_schema.dump(items),
        "page": pagination.page,
        "limit": pagination.limit,
        "total": total,
    }
    return deps.json_response(payload)


@api_v1.get("/routines/<int:routine_id>")
@deps.timing
def retrieve_routine(routine_id: int) -> Response:
    """Retrieve a single routine by identifier.

    :param routine_id: Routine identifier.
    :type routine_id: int
    :returns: Routine payload with ETag header.
    :rtype: flask.Response
    """

    # Acquire a session for database work.
    session = deps.get_session()
    routine = session.get(Routine, routine_id)
    if routine is None:
        return problem(status=HTTPStatus.NOT_FOUND, detail="Routine not found.", code="not_found")
    response = deps.json_response(routine_schema.dump(routine))
    return set_response_etag(response, routine)


@api_v1.post("/routines")
@deps.require_auth
@deps.require_scope("routines:write")
@deps.timing
def create_routine() -> Response:
    """Create a routine template.

    :returns: Serialized routine with ``201 Created``.
    :rtype: flask.Response
    """

    idempotency_key = request.headers.get("Idempotency-Key")
    is_replay, cached = deps.enforce_idempotency(idempotency_key)
    if is_replay and cached is not None:
        return deps.build_cached_response(cached)

    payload = request.get_json(silent=True) or {}
    data = routine_create_schema.load(payload)

    # Acquire a session for database work.
    session = deps.get_session()
    routine = Routine(**data)
    session.add(routine)
    session.commit()

    body = routine_schema.dump(routine)
    response = deps.json_response(body, status=HTTPStatus.CREATED)
    set_response_etag(response, routine)
    response.headers["Location"] = url_for("api_v1.retrieve_routine", routine_id=routine.id)
    headers = {"Location": response.headers["Location"]}
    if response.headers.get("ETag"):
        headers["ETag"] = response.headers["ETag"]
    deps.store_idempotent_response(
        idempotency_key,
        {"body": body, "status": HTTPStatus.CREATED, "headers": headers},
    )
    return response


@api_v1.patch("/routines/<int:routine_id>")
@deps.require_auth
@deps.require_scope("routines:write")
@deps.timing
def update_routine(routine_id: int) -> Response:
    """Patch routine metadata.

    :param routine_id: Routine identifier.
    :type routine_id: int
    :returns: Updated routine payload.
    :rtype: flask.Response
    """

    # Acquire a session for database work.
    session = deps.get_session()
    routine = session.get(Routine, routine_id)
    if routine is None:
        return problem(status=HTTPStatus.NOT_FOUND, detail="Routine not found.", code="not_found")

    if_match = request.headers.get("If-Match")
    if not if_match:
        return problem(status=HTTPStatus.PRECONDITION_FAILED, detail="Missing If-Match header.", code="missing_if_match")
    if not verify_etag(routine, if_match.strip('"')):
        return problem(status=HTTPStatus.PRECONDITION_FAILED, detail="ETag mismatch.", code="etag_mismatch")

    payload = request.get_json(silent=True) or {}
    data = routine_update_schema.load(payload)
    for key, value in data.items():
        setattr(routine, key, value)
    session.commit()

    response = deps.json_response(routine_schema.dump(routine))
    return set_response_etag(response, routine)


@api_v1.delete("/routines/<int:routine_id>")
@deps.require_auth
@deps.require_scope("routines:write")
@deps.timing
def delete_routine(routine_id: int) -> Response:
    """Delete a routine and its hierarchy.

    :param routine_id: Routine identifier.
    :type routine_id: int
    :returns: ``204 No Content`` when deletion succeeds.
    :rtype: flask.Response
    """

    # Acquire a session for database work.
    session = deps.get_session()
    routine = session.get(Routine, routine_id)
    if routine is None:
        return problem(status=HTTPStatus.NOT_FOUND, detail="Routine not found.", code="not_found")

    if_match = request.headers.get("If-Match")
    if not if_match:
        return problem(status=HTTPStatus.PRECONDITION_FAILED, detail="Missing If-Match header.", code="missing_if_match")
    if not verify_etag(routine, if_match.strip('"')):
        return problem(status=HTTPStatus.PRECONDITION_FAILED, detail="ETag mismatch.", code="etag_mismatch")

    session.delete(routine)
    session.commit()
    return Response(status=HTTPStatus.NO_CONTENT)


@api_v1.get("/routines/<int:routine_id>/days")
@deps.timing
def list_routine_days(routine_id: int) -> Response:
    """List routine days for a template.

    :param routine_id: Routine identifier.
    :type routine_id: int
    :returns: Collection of routine days.
    :rtype: flask.Response
    """

    # Acquire a session for database work.
    session = deps.get_session()
    routine = session.get(Routine, routine_id)
    if routine is None:
        return problem(status=HTTPStatus.NOT_FOUND, detail="Routine not found.", code="not_found")

    query = session.query(RoutineDay).filter(RoutineDay.routine_id == routine.id)
    pagination = deps.parse_pagination()
    sort_map = {"day_index": RoutineDay.day_index}
    query = deps.apply_sorting(query, sort_map, pagination.sort or ["day_index"])
    items, total = deps.paginate_query(query, pagination)
    payload = {
        "items": routine_days_schema.dump(items),
        "page": pagination.page,
        "limit": pagination.limit,
        "total": total,
    }
    return deps.json_response(payload)


@api_v1.post("/routines/<int:routine_id>/days")
@deps.require_auth
@deps.require_scope("routines:write")
@deps.timing
def create_routine_day(routine_id: int) -> Response:
    """Create a routine day entry.

    :param routine_id: Parent routine identifier.
    :type routine_id: int
    :returns: Created routine day payload.
    :rtype: flask.Response
    """

    idempotency_key = request.headers.get("Idempotency-Key")
    is_replay, cached = deps.enforce_idempotency(idempotency_key)
    if is_replay and cached is not None:
        return deps.build_cached_response(cached)

    # Acquire a session for database work.
    session = deps.get_session()
    routine = session.get(Routine, routine_id)
    if routine is None:
        return problem(status=HTTPStatus.NOT_FOUND, detail="Routine not found.", code="not_found")

    payload = request.get_json(silent=True) or {}
    data = routine_day_schema.load(payload)
    day = RoutineDay(routine_id=routine.id, **data)
    session.add(day)
    session.commit()

    body = routine_day_schema.dump(day)
    response = deps.json_response(body, status=HTTPStatus.CREATED)
    set_response_etag(response, day)
    response.headers["Location"] = url_for("api_v1.get_routine_day", routine_id=routine.id, day_id=day.id)
    headers = {"Location": response.headers["Location"]}
    if response.headers.get("ETag"):
        headers["ETag"] = response.headers["ETag"]
    deps.store_idempotent_response(
        idempotency_key,
        {"body": body, "status": HTTPStatus.CREATED, "headers": headers},
    )
    return response


@api_v1.get("/routines/<int:routine_id>/days/<int:day_id>")
@deps.timing
def get_routine_day(routine_id: int, day_id: int) -> Response:
    """Retrieve a routine day.

    :param routine_id: Parent routine identifier.
    :type routine_id: int
    :param day_id: Routine day identifier.
    :type day_id: int
    :returns: Serialized routine day payload.
    :rtype: flask.Response
    """

    # Acquire a session for database work.
    session = deps.get_session()
    day = (
        session.query(RoutineDay)
        .filter(RoutineDay.routine_id == routine_id, RoutineDay.id == day_id)
        .first()
    )
    if day is None:
        return problem(status=HTTPStatus.NOT_FOUND, detail="Routine day not found.", code="not_found")
    response = deps.json_response(routine_day_schema.dump(day))
    return set_response_etag(response, day)


@api_v1.patch("/routines/<int:routine_id>/days/<int:day_id>")
@deps.require_auth
@deps.require_scope("routines:write")
@deps.timing
def update_routine_day(routine_id: int, day_id: int) -> Response:
    """Patch a routine day.

    :param routine_id: Parent routine identifier.
    :type routine_id: int
    :param day_id: Routine day identifier.
    :type day_id: int
    :returns: Updated routine day payload.
    :rtype: flask.Response
    """

    # Acquire a session for database work.
    session = deps.get_session()
    day = (
        session.query(RoutineDay)
        .filter(RoutineDay.routine_id == routine_id, RoutineDay.id == day_id)
        .first()
    )
    if day is None:
        return problem(status=HTTPStatus.NOT_FOUND, detail="Routine day not found.", code="not_found")

    if_match = request.headers.get("If-Match")
    if not if_match:
        return problem(status=HTTPStatus.PRECONDITION_FAILED, detail="Missing If-Match header.", code="missing_if_match")
    if not verify_etag(day, if_match.strip('"')):
        return problem(status=HTTPStatus.PRECONDITION_FAILED, detail="ETag mismatch.", code="etag_mismatch")

    payload = request.get_json(silent=True) or {}
    data = routine_day_update_schema.load(payload)
    for key, value in data.items():
        setattr(day, key, value)
    session.commit()
    response = deps.json_response(routine_day_schema.dump(day))
    return set_response_etag(response, day)


@api_v1.delete("/routines/<int:routine_id>/days/<int:day_id>")
@deps.require_auth
@deps.require_scope("routines:write")
@deps.timing
def delete_routine_day(routine_id: int, day_id: int) -> Response:
    """Delete a routine day."""

    # Acquire a session for database work.
    session = deps.get_session()
    day = (
        session.query(RoutineDay)
        .filter(RoutineDay.routine_id == routine_id, RoutineDay.id == day_id)
        .first()
    )
    if day is None:
        return problem(status=HTTPStatus.NOT_FOUND, detail="Routine day not found.", code="not_found")

    if_match = request.headers.get("If-Match")
    if not if_match:
        return problem(status=HTTPStatus.PRECONDITION_FAILED, detail="Missing If-Match header.", code="missing_if_match")
    if not verify_etag(day, if_match.strip('"')):
        return problem(status=HTTPStatus.PRECONDITION_FAILED, detail="ETag mismatch.", code="etag_mismatch")

    session.delete(day)
    session.commit()
    return Response(status=HTTPStatus.NO_CONTENT)


@api_v1.get("/routines/<int:routine_id>/days/<int:day_id>/exercises")
@deps.timing
def list_routine_day_exercises(routine_id: int, day_id: int) -> Response:
    """List exercises configured for a routine day."""

    # Acquire a session for database work.
    session = deps.get_session()
    day = (
        session.query(RoutineDay)
        .filter(RoutineDay.routine_id == routine_id, RoutineDay.id == day_id)
        .first()
    )
    if day is None:
        return problem(status=HTTPStatus.NOT_FOUND, detail="Routine day not found.", code="not_found")

    query = session.query(RoutineDayExercise).filter(RoutineDayExercise.routine_day_id == day.id)
    pagination = deps.parse_pagination()
    sort_map = {"position": RoutineDayExercise.position}
    query = deps.apply_sorting(query, sort_map, pagination.sort or ["position"])
    items, total = deps.paginate_query(query, pagination)
    payload = {
        "items": routine_day_exercises_schema.dump(items),
        "page": pagination.page,
        "limit": pagination.limit,
        "total": total,
    }
    return deps.json_response(payload)


@api_v1.post("/routines/<int:routine_id>/days/<int:day_id>/exercises")
@deps.require_auth
@deps.require_scope("routines:write")
@deps.timing
def create_routine_day_exercise(routine_id: int, day_id: int) -> Response:
    """Create a planned exercise for a routine day."""

    idempotency_key = request.headers.get("Idempotency-Key")
    is_replay, cached = deps.enforce_idempotency(idempotency_key)
    if is_replay and cached is not None:
        return deps.build_cached_response(cached)

    # Acquire a session for database work.
    session = deps.get_session()
    day = (
        session.query(RoutineDay)
        .filter(RoutineDay.routine_id == routine_id, RoutineDay.id == day_id)
        .first()
    )
    if day is None:
        return problem(status=HTTPStatus.NOT_FOUND, detail="Routine day not found.", code="not_found")

    payload = request.get_json(silent=True) or {}
    data = routine_day_exercise_schema.load(payload)
    exercise = RoutineDayExercise(routine_day_id=day.id, **data)
    session.add(exercise)
    session.commit()

    body = routine_day_exercise_schema.dump(exercise)
    response = deps.json_response(body, status=HTTPStatus.CREATED)
    set_response_etag(response, exercise)
    response.headers["Location"] = url_for(
        "api_v1.get_routine_day_exercise", routine_id=routine_id, day_id=day_id, exercise_id=exercise.id
    )
    headers = {"Location": response.headers["Location"]}
    if response.headers.get("ETag"):
        headers["ETag"] = response.headers["ETag"]
    deps.store_idempotent_response(
        idempotency_key,
        {"body": body, "status": HTTPStatus.CREATED, "headers": headers},
    )
    return response


@api_v1.get("/routines/<int:routine_id>/days/<int:day_id>/exercises/<int:exercise_id>")
@deps.timing
def get_routine_day_exercise(routine_id: int, day_id: int, exercise_id: int) -> Response:
    """Retrieve a routine day exercise entry."""

    # Acquire a session for database work.
    session = deps.get_session()
    exercise = (
        session.query(RoutineDayExercise)
        .filter(
            RoutineDayExercise.routine_day_id == day_id,
            RoutineDayExercise.id == exercise_id,
            RoutineDayExercise.routine_day.has(RoutineDay.routine_id == routine_id),
        )
        .first()
    )
    if exercise is None:
        return problem(status=HTTPStatus.NOT_FOUND, detail="Routine day exercise not found.", code="not_found")
    response = deps.json_response(routine_day_exercise_schema.dump(exercise))
    return set_response_etag(response, exercise)


@api_v1.patch(
    "/routines/<int:routine_id>/days/<int:day_id>/exercises/<int:exercise_id>"
)
@deps.require_auth
@deps.require_scope("routines:write")
@deps.timing
def update_routine_day_exercise(routine_id: int, day_id: int, exercise_id: int) -> Response:
    """Patch a routine day exercise."""

    # Acquire a session for database work.
    session = deps.get_session()
    exercise = (
        session.query(RoutineDayExercise)
        .filter(
            RoutineDayExercise.routine_day_id == day_id,
            RoutineDayExercise.id == exercise_id,
            RoutineDayExercise.routine_day.has(RoutineDay.routine_id == routine_id),
        )
        .first()
    )
    if exercise is None:
        return problem(status=HTTPStatus.NOT_FOUND, detail="Routine day exercise not found.", code="not_found")

    if_match = request.headers.get("If-Match")
    if not if_match:
        return problem(status=HTTPStatus.PRECONDITION_FAILED, detail="Missing If-Match header.", code="missing_if_match")
    if not verify_etag(exercise, if_match.strip('"')):
        return problem(status=HTTPStatus.PRECONDITION_FAILED, detail="ETag mismatch.", code="etag_mismatch")

    payload = request.get_json(silent=True) or {}
    data = routine_day_exercise_update_schema.load(payload)
    for key, value in data.items():
        setattr(exercise, key, value)
    session.commit()
    response = deps.json_response(routine_day_exercise_schema.dump(exercise))
    return set_response_etag(response, exercise)


@api_v1.delete(
    "/routines/<int:routine_id>/days/<int:day_id>/exercises/<int:exercise_id>"
)
@deps.require_auth
@deps.require_scope("routines:write")
@deps.timing
def delete_routine_day_exercise(routine_id: int, day_id: int, exercise_id: int) -> Response:
    """Delete a routine day exercise."""

    # Acquire a session for database work.
    session = deps.get_session()
    exercise = (
        session.query(RoutineDayExercise)
        .filter(
            RoutineDayExercise.routine_day_id == day_id,
            RoutineDayExercise.id == exercise_id,
            RoutineDayExercise.routine_day.has(RoutineDay.routine_id == routine_id),
        )
        .first()
    )
    if exercise is None:
        return problem(status=HTTPStatus.NOT_FOUND, detail="Routine day exercise not found.", code="not_found")

    if_match = request.headers.get("If-Match")
    if not if_match:
        return problem(status=HTTPStatus.PRECONDITION_FAILED, detail="Missing If-Match header.", code="missing_if_match")
    if not verify_etag(exercise, if_match.strip('"')):
        return problem(status=HTTPStatus.PRECONDITION_FAILED, detail="ETag mismatch.", code="etag_mismatch")

    session.delete(exercise)
    session.commit()
    return Response(status=HTTPStatus.NO_CONTENT)


@api_v1.get(
    "/routines/<int:routine_id>/days/<int:day_id>/exercises/<int:exercise_id>/sets"
)
@deps.timing
def list_routine_sets(routine_id: int, day_id: int, exercise_id: int) -> Response:
    """List planned sets for a routine day exercise."""

    # Acquire a session for database work.
    session = deps.get_session()
    exercise = (
        session.query(RoutineDayExercise)
        .filter(
            RoutineDayExercise.routine_day_id == day_id,
            RoutineDayExercise.id == exercise_id,
            RoutineDayExercise.routine_day.has(RoutineDay.routine_id == routine_id),
        )
        .first()
    )
    if exercise is None:
        return problem(status=HTTPStatus.NOT_FOUND, detail="Routine day exercise not found.", code="not_found")

    query = session.query(RoutineExerciseSet).filter(RoutineExerciseSet.routine_day_exercise_id == exercise.id)
    pagination = deps.parse_pagination()
    sort_map = {"set_index": RoutineExerciseSet.set_index}
    query = deps.apply_sorting(query, sort_map, pagination.sort or ["set_index"])
    items, total = deps.paginate_query(query, pagination)
    payload = {
        "items": routine_sets_schema.dump(items),
        "page": pagination.page,
        "limit": pagination.limit,
        "total": total,
    }
    return deps.json_response(payload)


@api_v1.post(
    "/routines/<int:routine_id>/days/<int:day_id>/exercises/<int:exercise_id>/sets"
)
@deps.require_auth
@deps.require_scope("routines:write")
@deps.timing
def create_routine_set(routine_id: int, day_id: int, exercise_id: int) -> Response:
    """Create a planned set for a routine exercise."""

    idempotency_key = request.headers.get("Idempotency-Key")
    is_replay, cached = deps.enforce_idempotency(idempotency_key)
    if is_replay and cached is not None:
        return deps.build_cached_response(cached)

    # Acquire a session for database work.
    session = deps.get_session()
    exercise = (
        session.query(RoutineDayExercise)
        .filter(
            RoutineDayExercise.routine_day_id == day_id,
            RoutineDayExercise.id == exercise_id,
            RoutineDayExercise.routine_day.has(RoutineDay.routine_id == routine_id),
        )
        .first()
    )
    if exercise is None:
        return problem(status=HTTPStatus.NOT_FOUND, detail="Routine day exercise not found.", code="not_found")

    payload = request.get_json(silent=True) or {}
    data = routine_set_schema.load(payload)
    routine_set = RoutineExerciseSet(routine_day_exercise_id=exercise.id, **data)
    session.add(routine_set)
    session.commit()

    body = routine_set_schema.dump(routine_set)
    response = deps.json_response(body, status=HTTPStatus.CREATED)
    set_response_etag(response, routine_set)
    response.headers["Location"] = url_for(
        "api_v1.get_routine_set",
        routine_id=routine_id,
        day_id=day_id,
        exercise_id=exercise_id,
        set_id=routine_set.id,
    )
    headers = {"Location": response.headers["Location"]}
    if response.headers.get("ETag"):
        headers["ETag"] = response.headers["ETag"]
    deps.store_idempotent_response(
        idempotency_key,
        {"body": body, "status": HTTPStatus.CREATED, "headers": headers},
    )
    return response


@api_v1.get(
    "/routines/<int:routine_id>/days/<int:day_id>/exercises/<int:exercise_id>/sets/<int:set_id>"
)
@deps.timing
def get_routine_set(routine_id: int, day_id: int, exercise_id: int, set_id: int) -> Response:
    """Retrieve a planned set."""

    # Acquire a session for database work.
    session = deps.get_session()
    routine_set = (
        session.query(RoutineExerciseSet)
        .join(RoutineDayExercise)
        .filter(
            RoutineExerciseSet.id == set_id,
            RoutineExerciseSet.routine_day_exercise_id == exercise_id,
            RoutineDayExercise.routine_day_id == day_id,
            RoutineDayExercise.routine_day.has(RoutineDay.routine_id == routine_id),
        )
        .first()
    )
    if routine_set is None:
        return problem(status=HTTPStatus.NOT_FOUND, detail="Routine set not found.", code="not_found")
    response = deps.json_response(routine_set_schema.dump(routine_set))
    return set_response_etag(response, routine_set)


@api_v1.patch(
    "/routines/<int:routine_id>/days/<int:day_id>/exercises/<int:exercise_id>/sets/<int:set_id>"
)
@deps.require_auth
@deps.require_scope("routines:write")
@deps.timing
def update_routine_set(
    routine_id: int, day_id: int, exercise_id: int, set_id: int
) -> Response:
    """Patch a planned routine set."""

    # Acquire a session for database work.
    session = deps.get_session()
    routine_set = (
        session.query(RoutineExerciseSet)
        .join(RoutineDayExercise)
        .filter(
            RoutineExerciseSet.id == set_id,
            RoutineExerciseSet.routine_day_exercise_id == exercise_id,
            RoutineDayExercise.routine_day_id == day_id,
            RoutineDayExercise.routine_day.has(RoutineDay.routine_id == routine_id),
        )
        .first()
    )
    if routine_set is None:
        return problem(status=HTTPStatus.NOT_FOUND, detail="Routine set not found.", code="not_found")

    if_match = request.headers.get("If-Match")
    if not if_match:
        return problem(status=HTTPStatus.PRECONDITION_FAILED, detail="Missing If-Match header.", code="missing_if_match")
    if not verify_etag(routine_set, if_match.strip('"')):
        return problem(status=HTTPStatus.PRECONDITION_FAILED, detail="ETag mismatch.", code="etag_mismatch")

    payload = request.get_json(silent=True) or {}
    data = routine_set_update_schema.load(payload)
    for key, value in data.items():
        setattr(routine_set, key, value)
    session.commit()
    response = deps.json_response(routine_set_schema.dump(routine_set))
    return set_response_etag(response, routine_set)


@api_v1.delete(
    "/routines/<int:routine_id>/days/<int:day_id>/exercises/<int:exercise_id>/sets/<int:set_id>"
)
@deps.require_auth
@deps.require_scope("routines:write")
@deps.timing
def delete_routine_set(routine_id: int, day_id: int, exercise_id: int, set_id: int) -> Response:
    """Delete a planned routine set."""

    # Acquire a session for database work.
    session = deps.get_session()
    routine_set = (
        session.query(RoutineExerciseSet)
        .join(RoutineDayExercise)
        .filter(
            RoutineExerciseSet.id == set_id,
            RoutineExerciseSet.routine_day_exercise_id == exercise_id,
            RoutineDayExercise.routine_day_id == day_id,
            RoutineDayExercise.routine_day.has(RoutineDay.routine_id == routine_id),
        )
        .first()
    )
    if routine_set is None:
        return problem(status=HTTPStatus.NOT_FOUND, detail="Routine set not found.", code="not_found")

    if_match = request.headers.get("If-Match")
    if not if_match:
        return problem(status=HTTPStatus.PRECONDITION_FAILED, detail="Missing If-Match header.", code="missing_if_match")
    if not verify_etag(routine_set, if_match.strip('"')):
        return problem(status=HTTPStatus.PRECONDITION_FAILED, detail="ETag mismatch.", code="etag_mismatch")

    session.delete(routine_set)
    session.commit()
    return Response(status=HTTPStatus.NO_CONTENT)
