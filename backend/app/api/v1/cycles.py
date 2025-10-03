"""Cycle and subject-routine endpoints."""

from __future__ import annotations

from http import HTTPStatus

from flask import Response, request, url_for

from app.models.cycle import Cycle
from app.models.routine import Routine, SubjectRoutine
from app.models.subject import Subject

from .. import deps
from ..errors import problem
from ..etag import set_response_etag, verify_etag
from ..schemas import (
    CycleSchema,
    CycleUpdateSchema,
    SubjectRoutineSchema,
)
from . import api_v1

cycle_schema = CycleSchema()
cycles_schema = CycleSchema(many=True)
cycle_update_schema = CycleUpdateSchema(partial=True)
subject_routine_schema = SubjectRoutineSchema()
subject_routines_schema = SubjectRoutineSchema(many=True)


@api_v1.get("/cycles")
@deps.timing
def list_cycles() -> Response:
    """List cycles filtered by subject, routine, or cycle number."""

    pagination = deps.parse_pagination()
    # Acquire a session for database work.
    session = deps.get_session()
    query = session.query(Cycle)

    subject_id = request.args.get("subject_id", type=int)
    routine_id = request.args.get("routine_id", type=int)
    cycle_number = request.args.get("cycle_number", type=int)

    if subject_id is not None:
        query = query.filter(Cycle.subject_id == subject_id)
    if routine_id is not None:
        query = query.filter(Cycle.routine_id == routine_id)
    if cycle_number is not None:
        query = query.filter(Cycle.cycle_number == cycle_number)

    sort_map = {"started_on": Cycle.started_on, "created_at": Cycle.created_at}
    query = deps.apply_sorting(query, sort_map, pagination.sort)

    items, total = deps.paginate_query(query, pagination)
    payload = {
        "items": cycles_schema.dump(items),
        "page": pagination.page,
        "limit": pagination.limit,
        "total": total,
    }
    return deps.json_response(payload)


@api_v1.get("/cycles/<int:cycle_id>")
@deps.timing
def retrieve_cycle(cycle_id: int) -> Response:
    """Retrieve a single cycle."""

    # Acquire a session for database work.
    session = deps.get_session()
    cycle = session.get(Cycle, cycle_id)
    if cycle is None:
        return problem(status=HTTPStatus.NOT_FOUND, detail="Cycle not found.", code="not_found")
    response = deps.json_response(cycle_schema.dump(cycle))
    return set_response_etag(response, cycle)


@api_v1.post("/cycles")
@deps.require_auth
@deps.require_scope("cycles:write")
@deps.timing
def create_cycle() -> Response:
    """Create a cycle linking a subject and routine."""

    idempotency_key = request.headers.get("Idempotency-Key")
    is_replay, cached = deps.enforce_idempotency(idempotency_key)
    if is_replay and cached is not None:
        return deps.build_cached_response(cached)

    payload = request.get_json(silent=True) or {}
    data = cycle_schema.load(payload)

    # Acquire a session for database work.
    session = deps.get_session()
    subject = session.get(Subject, data["subject_id"])
    routine = session.get(Routine, data["routine_id"])
    if subject is None or routine is None:
        return problem(status=HTTPStatus.UNPROCESSABLE_ENTITY, detail="Subject or routine not found.", code="invalid_reference")

    cycle = Cycle(**data)
    session.add(cycle)
    session.commit()

    body = cycle_schema.dump(cycle)
    response = deps.json_response(body, status=HTTPStatus.CREATED)
    set_response_etag(response, cycle)
    response.headers["Location"] = url_for("api_v1.retrieve_cycle", cycle_id=cycle.id)
    headers = {"Location": response.headers["Location"]}
    if response.headers.get("ETag"):
        headers["ETag"] = response.headers["ETag"]
    deps.store_idempotent_response(
        idempotency_key,
        {"body": body, "status": HTTPStatus.CREATED, "headers": headers},
    )
    return response


@api_v1.patch("/cycles/<int:cycle_id>")
@deps.require_auth
@deps.require_scope("cycles:write")
@deps.timing
def update_cycle(cycle_id: int) -> Response:
    """Patch cycle metadata such as dates or notes."""

    # Acquire a session for database work.
    session = deps.get_session()
    cycle = session.get(Cycle, cycle_id)
    if cycle is None:
        return problem(status=HTTPStatus.NOT_FOUND, detail="Cycle not found.", code="not_found")

    if_match = request.headers.get("If-Match")
    if not if_match:
        return problem(status=HTTPStatus.PRECONDITION_FAILED, detail="Missing If-Match header.", code="missing_if_match")
    if not verify_etag(cycle, if_match.strip('"')):
        return problem(status=HTTPStatus.PRECONDITION_FAILED, detail="ETag mismatch.", code="etag_mismatch")

    payload = request.get_json(silent=True) or {}
    data = cycle_update_schema.load(payload)
    for key, value in data.items():
        setattr(cycle, key, value)
    session.commit()
    response = deps.json_response(cycle_schema.dump(cycle))
    return set_response_etag(response, cycle)


@api_v1.delete("/cycles/<int:cycle_id>")
@deps.require_auth
@deps.require_scope("cycles:write")
@deps.timing
def delete_cycle(cycle_id: int) -> Response:
    """Delete a cycle."""

    # Acquire a session for database work.
    session = deps.get_session()
    cycle = session.get(Cycle, cycle_id)
    if cycle is None:
        return problem(status=HTTPStatus.NOT_FOUND, detail="Cycle not found.", code="not_found")

    if_match = request.headers.get("If-Match")
    if not if_match:
        return problem(status=HTTPStatus.PRECONDITION_FAILED, detail="Missing If-Match header.", code="missing_if_match")
    if not verify_etag(cycle, if_match.strip('"')):
        return problem(status=HTTPStatus.PRECONDITION_FAILED, detail="ETag mismatch.", code="etag_mismatch")

    session.delete(cycle)
    session.commit()
    return Response(status=HTTPStatus.NO_CONTENT)


@api_v1.get("/subject-routines")
@deps.timing
def list_subject_routines() -> Response:
    """List links between subjects and routines."""

    pagination = deps.parse_pagination()
    # Acquire a session for database work.
    session = deps.get_session()
    query = session.query(SubjectRoutine)

    subject_id = request.args.get("subject_id", type=int)
    routine_id = request.args.get("routine_id", type=int)
    is_active = request.args.get("is_active")

    if subject_id is not None:
        query = query.filter(SubjectRoutine.subject_id == subject_id)
    if routine_id is not None:
        query = query.filter(SubjectRoutine.routine_id == routine_id)
    if is_active is not None:
        query = query.filter(SubjectRoutine.is_active == (is_active.lower() != "false"))

    sort_map = {"saved_on": SubjectRoutine.saved_on}
    query = deps.apply_sorting(query, sort_map, pagination.sort)

    items, total = deps.paginate_query(query, pagination)
    payload = {
        "items": subject_routines_schema.dump(items),
        "page": pagination.page,
        "limit": pagination.limit,
        "total": total,
    }
    return deps.json_response(payload)


@api_v1.post("/subject-routines")
@deps.require_auth
@deps.require_scope("routines:write")
@deps.timing
def create_subject_routine() -> Response:
    """Create a subject-routine association."""

    idempotency_key = request.headers.get("Idempotency-Key")
    is_replay, cached = deps.enforce_idempotency(idempotency_key)
    if is_replay and cached is not None:
        return deps.build_cached_response(cached)

    payload = request.get_json(silent=True) or {}
    data = subject_routine_schema.load(payload)

    # Acquire a session for database work.
    session = deps.get_session()
    subject = session.get(Subject, data["subject_id"])
    routine = session.get(Routine, data["routine_id"])
    if subject is None or routine is None:
        return problem(status=HTTPStatus.UNPROCESSABLE_ENTITY, detail="Subject or routine not found.", code="invalid_reference")

    link = SubjectRoutine(**data)
    session.add(link)
    session.commit()

    body = subject_routine_schema.dump(link)
    response = deps.json_response(body, status=HTTPStatus.CREATED)
    set_response_etag(response, link)
    response.headers["Location"] = url_for("api_v1.get_subject_routine", link_id=link.id)
    headers = {"Location": response.headers["Location"]}
    if response.headers.get("ETag"):
        headers["ETag"] = response.headers["ETag"]
    deps.store_idempotent_response(
        idempotency_key,
        {"body": body, "status": HTTPStatus.CREATED, "headers": headers},
    )
    return response


@api_v1.get("/subject-routines/<int:link_id>")
@deps.timing
def get_subject_routine(link_id: int) -> Response:
    """Retrieve a subject-routine association."""

    # Acquire a session for database work.
    session = deps.get_session()
    link = session.get(SubjectRoutine, link_id)
    if link is None:
        return problem(status=HTTPStatus.NOT_FOUND, detail="Subject routine link not found.", code="not_found")
    response = deps.json_response(subject_routine_schema.dump(link))
    return set_response_etag(response, link)


@api_v1.delete("/subject-routines/<int:link_id>")
@deps.require_auth
@deps.require_scope("routines:write")
@deps.timing
def delete_subject_routine(link_id: int) -> Response:
    """Delete a subject-routine association."""

    # Acquire a session for database work.
    session = deps.get_session()
    link = session.get(SubjectRoutine, link_id)
    if link is None:
        return problem(status=HTTPStatus.NOT_FOUND, detail="Subject routine link not found.", code="not_found")

    if_match = request.headers.get("If-Match")
    if not if_match:
        return problem(status=HTTPStatus.PRECONDITION_FAILED, detail="Missing If-Match header.", code="missing_if_match")
    if not verify_etag(link, if_match.strip('"')):
        return problem(status=HTTPStatus.PRECONDITION_FAILED, detail="ETag mismatch.", code="etag_mismatch")

    session.delete(link)
    session.commit()
    return Response(status=HTTPStatus.NO_CONTENT)
