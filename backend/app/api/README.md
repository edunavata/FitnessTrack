# API Endpoint Map

The API follows a resource-oriented style under the `/api/v1` prefix. All
collection endpoints support `page`, `limit`, `sort`, and simple equality
filters. List responses use the envelope
`{"items": [...], "page": 1, "limit": 50, "total": 123}`. Partial updates
require `If-Match` with entity ETags derived from `updated_at` and primary keys.

## System

| Resource | URI | Notes |
| --- | --- | --- |
| Health | `GET /api/v1/health` | Returns process, DB connectivity, and latency telemetry. |

## Users

| Resource | URI | Filters / Query params | Relationships |
| --- | --- | --- | --- |
| Users collection | `GET /api/v1/users` | `email`, `username`, `sort` (`id`, `created_at`, `username`) | Links to a single `Subject` (if any). |
| User detail | `GET /api/v1/users/{user_id}` | — | Returns subject linkage metadata. |
| Create user | `POST /api/v1/users` | Requires `Idempotency-Key` for safe retries. | Creates optional subject association via `subject_id`. |
| Update user | `PATCH /api/v1/users/{user_id}` | Requires `If-Match`. | Allows updating profile-safe fields (`username`, `full_name`, password reset). |
| Delete user | `DELETE /api/v1/users/{user_id}` | Hard delete (subject anonymization handled separately). | Cascade severed through FK rules. |

## Subjects & Profiles

| Resource | URI | Filters / Query params | Relationships |
| --- | --- | --- | --- |
| Subjects | `GET /api/v1/subjects` | `user_id`, `pseudonym`, `sort` (`id`, `created_at`) | Owners of routines, cycles, workouts, logs. |
| Subject detail | `GET /api/v1/subjects/{subject_id}` | — | Includes link to profile route. |
| Create subject | `POST /api/v1/subjects` | Idempotent via header. | Optional `user_id` link. |
| Update subject | `PATCH /api/v1/subjects/{subject_id}` | Requires `If-Match`. | Supports unlinking user for GDPR deletion. |
| Delete subject | `DELETE /api/v1/subjects/{subject_id}` | Hard delete (domain cascade). | Removes dependent records via FK `ON DELETE CASCADE`. |
| Subject profile | `GET /api/v1/subjects/{subject_id}/profile` | — | 1:1; returns 404 if missing. |
| Replace profile | `PUT /api/v1/subjects/{subject_id}/profile` | Requires `If-Match` when existing. | Creates or replaces the profile document. |
| Body metrics collection | `GET /api/v1/subjects/{subject_id}/body-metrics` | `measured_on`, `sort` (`measured_on desc` default). | Time-series of indirect PII. |
| Body metric detail | `GET /api/v1/subjects/{subject_id}/body-metrics/{metric_id}` | — | Scoped to owner subject. |
| Create body metric | `POST /api/v1/subjects/{subject_id}/body-metrics` | Idempotent via header. | Requires `measured_on`. |
| Update body metric | `PATCH /api/v1/subjects/{subject_id}/body-metrics/{metric_id}` | Requires `If-Match`. | Partial merge, e.g., adjusting weight. |
| Delete body metric | `DELETE /api/v1/subjects/{subject_id}/body-metrics/{metric_id}` | Hard delete. | Removes a single measurement. |

## Exercises & Taxonomy

| Resource | URI | Filters / Query params | Relationships |
| --- | --- | --- | --- |
| Exercises | `GET /api/v1/exercises` | `name`, `primary_muscle`, `equipment`, `is_active`, `sort` (`name`, `created_at`, `difficulty`) | Related to routine templates and performed logs. |
| Exercise detail | `GET /api/v1/exercises/{exercise_id}` | — | Includes alias/tag links. |
| Create exercise | `POST /api/v1/exercises` | Requires `Idempotency-Key`. | Accepts secondary muscles, aliases, tags arrays. |
| Update exercise | `PATCH /api/v1/exercises/{exercise_id}` | Requires `If-Match`. | Partial update of metadata and active status. |
| Delete exercise | `DELETE /api/v1/exercises/{exercise_id}` | Soft delete simulated by toggling `is_active`. |
| Reference enums | `GET /api/v1/exercises/meta/{enum_name}` | — | Exposes enumerations (`muscle_groups`, `equipment`, `movement_patterns`, `levels`, `force_vectors`, `mechanics`). |

## Routines & Templates

| Resource | URI | Filters / Query params | Relationships |
| --- | --- | --- | --- |
| Routines | `GET /api/v1/routines` | `owner_subject_id`, `is_public`, `name`, `sort` (`created_at`, `name`) | Owns `routine_days`, `subject_routines`, and `cycles`. |
| Routine detail | `GET /api/v1/routines/{routine_id}` | — | Includes summary counts. |
| Create routine | `POST /api/v1/routines` | Requires `Idempotency-Key`. | Body accepts initial sharing flag. |
| Update routine | `PATCH /api/v1/routines/{routine_id}` | Requires `If-Match`. | Adjust metadata and activation state. |
| Delete routine | `DELETE /api/v1/routines/{routine_id}` | Hard delete; cascades to template hierarchy. |
| Routine days | `GET /api/v1/routines/{routine_id}/days` | `sort` (`day_index`). | Child-only resource. |
| Routine day detail | `GET /api/v1/routines/{routine_id}/days/{day_id}` | — | Contains exercises and notes. |
| Create/Update/Delete routine day | `POST`, `PATCH`, `DELETE /api/v1/routines/{routine_id}/days` | Idempotency for create; `If-Match` for updates. | Maintains ordering via `day_index`. |
| Routine day exercises | `GET /api/v1/routines/{routine_id}/days/{day_id}/exercises` | `sort` (`position`). | Sequence of exercises referencing catalog. |
| Routine exercise sets | `GET /api/v1/routines/{routine_id}/days/{day_id}/exercises/{exercise_id}/sets` | — | Planned targets per set. |

## Subject Routine Library

| Resource | URI | Filters / Query params | Relationships |
| --- | --- | --- | --- |
| Subject routine links | `GET /api/v1/subject-routines` | `subject_id`, `routine_id`, `is_active` | Connects subjects to shared/public routines. |
| Create link | `POST /api/v1/subject-routines` | Requires `Idempotency-Key`. | Adds saved routine reference. |
| Delete link | `DELETE /api/v1/subject-routines/{link_id}` | — | Removes saved routine. |

## Cycles & Execution

| Resource | URI | Filters / Query params | Relationships |
| --- | --- | --- | --- |
| Cycles | `GET /api/v1/cycles` | `subject_id`, `routine_id`, `cycle_number`, `sort` (`started_on`, `created_at`) | Binds template to execution window. |
| Cycle detail | `GET /api/v1/cycles/{cycle_id}` | — | Includes related session count summary. |
| Create cycle | `POST /api/v1/cycles` | Requires `Idempotency-Key`. | Enforces `(subject_id, routine_id, cycle_number)` uniqueness. |
| Update cycle | `PATCH /api/v1/cycles/{cycle_id}` | Requires `If-Match`. | Adjust dates, notes. |
| Delete cycle | `DELETE /api/v1/cycles/{cycle_id}` | Hard delete; dependent sessions set `NULL`. |

## Workout Sessions & Logs

| Resource | URI | Filters / Query params | Relationships |
| --- | --- | --- | --- |
| Workout sessions | `GET /api/v1/workouts/sessions` | `subject_id`, `status`, `from`, `to`, `sort` (`workout_date`, `created_at`) | Optionally linked to `routine_day` and `cycle`. |
| Session detail | `GET /api/v1/workouts/sessions/{session_id}` | — | Includes basic relation metadata. |
| Create session | `POST /api/v1/workouts/sessions` | Requires `Idempotency-Key`. | Validates subject/cycle pairing. |
| Update session | `PATCH /api/v1/workouts/sessions/{session_id}` | Requires `If-Match`. | Partial update for status, fatigue metrics. |
| Delete session | `DELETE /api/v1/workouts/sessions/{session_id}` | Hard delete. |
| Exercise set logs | `GET /api/v1/workouts/set-logs` | `subject_id`, `exercise_id`, `session_id`, `from`, `to`, `sort` (`performed_at`) | Links actual sets to planned sets. |
| Set log detail | `GET /api/v1/workouts/set-logs/{log_id}` | — | Returns session/planned linkage. |
| Create set log | `POST /api/v1/workouts/set-logs` | Requires `Idempotency-Key`. | Enforces subject consistency with linked session. |
| Update set log | `PATCH /api/v1/workouts/set-logs/{log_id}` | Requires `If-Match`. | Partial adjustments for actual values. |
| Delete set log | `DELETE /api/v1/workouts/set-logs/{log_id}` | Hard delete. |

## Reference Data

| Resource | URI | Notes |
| --- | --- | --- |
| Enumerations | `GET /api/v1/reference/{name}` | Mirrors database enums when not tied to exercises (e.g., `sex`, `workout_status`). |

## Rationale

- **Resource boundaries** mirror SQLAlchemy models, promoting clarity between
  template data (`routines`, `routine_days`, `routine_day_exercises`,
  `routine_exercise_sets`) and execution data (`cycles`, `workout_sessions`,
  `exercise_set_logs`). Hierarchical URIs are only used for entities that cannot
  exist independently (`routine_days`, subject profiles, body metrics),
  preserving top-level access for shareable resources (`routines`, `cycles`).
- **Versioned prefix** `/api/v1` isolates the contract for evolution. Future
  iterations can register additional blueprints without breaking the factory.
- **Pagination and sorting** are consistent across collections to keep client
  ergonomics predictable and to guard against unbounded queries.
- **Problem Details** (RFC 7807 / RFC 9457) unify error payloads, ensuring
  machine-readable `type`, `code`, and `errors` arrays when validation fails.
- **Concurrency safety** leans on ETags derived from `(id, updated_at)` for
  optimistic locking via `If-Match`, while `Idempotency-Key` headers prevent
  duplicate writes in retry scenarios.
- **Security** stubs enforce bearer-token presence on mutating endpoints and
  leave clear TODO markers for scope/role checks, aligning with future JWT
  adoption.
