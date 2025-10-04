# Repository Layer Reference

## Overview

### What is a Repository in this codebase
- Repositories provide persistence-only CRUD helpers over SQLAlchemy ORM models.
- They are thin facades around `BaseRepository`, offering typed utilities for a
  single aggregate root and its direct relationships.
- Query composition (filters, sorting, eager loading) lives in the repository; it
  does **not** enforce domain rules or coordinate workflows.

### Boundaries: persistence-only, no business logic, no commits
- Repositories **never** call `commit()` or `rollback()`; the service layer owns
  transaction lifecycles and the Unit of Work.
- Business invariants (permissions, orchestration, validations that span
  aggregates) belong to services or domain services.
- Methods may call `session.flush()` when they need database-generated values
  (PKs, defaults) but leave the transaction open for the caller.

### Transaction model and session ownership
- Every repository resolves the session through `BaseRepository.session`, which
  proxies `db.session` from the Flask SQLAlchemy extension.
- Callers must manage transaction boundaries explicitly; repositories assume an
  active session context.
- Because repositories avoid implicit commits, they can be composed safely within
  larger service-level transactions.

## Base Repository (the core)

### Responsibilities
- Generic CRUD helpers (`add`, `get`, `delete`, `update`) with type-safe
  signatures powered by generics.
- Deterministic listing APIs (`list`, `paginate`) that apply filtering,
  whitelisted sorting, eager loading, and a primary-key tiebreaker.
- Pagination utilities (`Pagination`, `Page`, `paginate_select`) to execute
  limited queries with optional total counting.
- Safe update helpers that whitelist fields and raise when unknown keys are
  encountered (fail-closed default).

### Sorting whitelist & security
- Sorting uses `_apply_sorting` which maps public sort tokens to ORM attributes
  defined in each repository's `_sortable_fields()` override.
- Unknown sort keys are ignored, preventing SQL injection through dynamic `ORDER
  BY` clauses.
- The model's primary key is appended as a final ascending tiebreaker so paging
  remains stable across requests.

### `_default_eagerload` contract and guidance for subclasses
- Subclasses override `_default_eagerload(stmt)` to attach eager-loading options
  suited for their aggregate.
- Collections typically use `selectinload()` to avoid row explosion and the need
  for `Result.unique()`.
- Many-to-one / scalar relationships use `joinedload()` when the joined columns
  are lightweight and help reduce round-trips.
- The method must return a new `Select` object (SQLAlchemy is immutable here),
  allowing base helpers to chain additional options.

### Typing & generics
- `BaseRepository` is generic in the SQLAlchemy mapped entity (`BaseRepository[E]`).
- Dataclasses `Pagination` and `Page[E]` expose typed items and metadata.
- Whitelist maps use `InstrumentedAttribute[Any]` to reflect SQLAlchemy 2.0 typing.

### Error handling philosophy
- Methods raise `ValueError` for misuse (unknown update keys, empty inputs) and
  `RuntimeError` when required metadata (e.g., a detectable primary key) is
  missing.
- SQLAlchemy validation hooks (via `@validates` or property setters) are relied
  upon; repositories surface those errors without wrapping.

## Eager Loading Strategy

- Prefer `selectinload()` for one-to-many or many-to-many collections to avoid
  Cartesian product expansion and to keep pagination efficient.
- Use `joinedload()` for scalar or many-to-one relationships when it eliminates
  an extra round-trip (e.g., loading a profile with each subject).
- Only opt into eager loading in `_default_eagerload()` when consumers need the
  related data for the common read paths; keep listings lean by default.

## Per-Repository Notes

### `CycleRepository`
- **Entity**: `Cycle` linked to `Subject` and `Routine`; unique key on
  `(subject_id, routine_id, cycle_number)`.
- **Key methods**: `get_by_unique`, `next_cycle_number`, `ensure_cycle_number`,
  `create_cycle`, `paginate_for_subject`.
- **Patterns**: Deterministic sorting via cycle number, subject/routine scoped
  listings; `ensure_cycle_number` queries the next number to avoid uniqueness
  conflicts.
- **Gotchas**: Callers should provide explicit cycle numbers only when enforcing
  their own sequencing; otherwise rely on the helper to respect uniqueness.

### `ExerciseRepository`
- **Entity**: `Exercise` with aliases, tags, and secondary muscle associations.
- **Key methods**: `add_alias`, `remove_alias`, `set_tags_by_names`,
  `add_tags`, `remove_tags`, `list_by_tag`, `set_secondary_muscles`.
- **Patterns**: Uses `selectinload` for collections and joined loading of tag
  names; tag helpers ensure idempotency and cleanup unused links.
- **Gotchas**: Tag creation flushes to obtain PKs; secondary muscles are stored
  uppercase and deduplicated server-side.

### `ExerciseSetLogRepository`
- **Entity**: `ExerciseSetLog` time-series keyed by `(subject, exercise,
  performed_at, set_index)`.
- **Key methods**: `create_log`, `upsert_log`, `list_for_subject`,
  `paginate_for_subject`, `list_for_session`, `latest_for_subject_exercise`.
- **Patterns**: Date filtering converts date bounds to timezone-aware datetimes;
  upserts mutate only provided fields to preserve immutability of keys.
- **Gotchas**: Validators on the model enforce subject/session consistency and
  will raise when mismatched.

### `RoutineRepository`
- **Entity**: `Routine` aggregate with `RoutineDay`, `RoutineDayExercise`, and
  `RoutineExerciseSet` children.
- **Key methods**: `add_day`, `add_exercise_to_day`, `upsert_set`,
  `paginate_public`, `list_by_owner`, `list_public`.
- **Patterns**: `selectinload` for nested collections to avoid duplicate rows;
  sequential indexes computed via helper queries.
- **Gotchas**: Upserting sets requires explicit `set_index`; the repository does
  not re-order existing records.

### `SubjectRoutineRepository`
- **Entity**: Association table linking subjects to routines they saved.
- **Key methods**: `save`, `remove`, `set_active`, `list_saved_by_subject`.
- **Patterns**: `save` is idempotent and defaults new links to inactive to
  sidestep backend-specific defaults.
- **Gotchas**: Active flag toggles rely on the model validator to ensure subject
  ownership of associated routines.

### `SubjectRepository`
- **Entity**: `Subject` with a 1:1 `SubjectProfile` relationship.
- **Key methods**: `get_by_user_id`, `get_by_pseudonym`, `ensure_profile`,
  `update_profile`.
- **Patterns**: Uses `joinedload` for the profile to keep lookups efficient;
  profile updates convert string inputs to enums when necessary.
- **Gotchas**: `ensure_profile` flushes when creating the profile to populate
  the identity map; callers should expect a `RuntimeError` for unknown subjects.

### `SubjectBodyMetricsRepository`
- **Entity**: `SubjectBodyMetrics` time-series per subject/date.
- **Key methods**: `list_for_subject`, `paginate_for_subject`, `upsert_by_day`.
- **Patterns**: Range queries filter on `measured_on`; upsert assigns via
  `setattr` to reuse validators.
- **Gotchas**: Sorting always includes the PK tiebreaker ensuring stable
  chronological pagination.

### `TagRepository`
- **Entity**: `Tag` referenced by exercises.
- **Key methods**: `get_by_name`, `ensure`, inherited update helpers.
- **Patterns**: Simplified repository that mainly ensures tag existence before
  relationship creation.
- **Gotchas**: `ensure` trims and validates non-empty names, raising on invalid
  input.

### `UserRepository`
- **Entity**: `User` model responsible for authentication metadata.
- **Key methods**: `get_by_email`, `exists_by_email`, `update_password`,
  `authenticate`, inherited `assign_updates`.
- **Patterns**: Emails are normalised to lowercase; password updates rely on the
  model's setter to hash values.
- **Gotchas**: Authentication simply checks password validity; higher-level
  services should handle lockouts or throttling.

### `WorkoutSessionRepository`
- **Entity**: `WorkoutSession` keyed by `(subject_id, workout_date)`.
- **Key methods**: `create_session`, `upsert_by_date`, `attach_to_cycle`,
  `mark_completed`, `list_for_subject`, `paginate_for_subject`, `list_for_cycle`.
- **Patterns**: Date filtering mirrors set-log logic by converting inclusive date
  bounds to timezone-aware datetimes; updates whitelist excludes logical key
  fields.
- **Gotchas**: Cycle attachments rely on model validators to ensure the session
  and cycle share the same subject; mismatches raise `ValueError`.

## Examples

### Listing with filtering and sorting
```python
repo = ExerciseRepository()
rows = repo.list(filters={"is_active": True}, sort=["name", "-created_at"])
for exercise in rows:
    print(exercise.name, exercise.created_at)
```

### Paginating with deterministic ordering
```python
repo = WorkoutSessionRepository()
page = repo.paginate_for_subject(
    Pagination(page=1, limit=20, sort=["-workout_date"]),
    subject_id=current_subject.id,
    with_total=True,
)
print(f"Total sessions: {page.total}")
for session in page.items:
    print(session.workout_date, session.status)
```

### Fetching with eager loading
```python
repo = SubjectRepository()
subject = repo.get_by_user_id(current_user.id)
if subject and subject.profile:
    print(subject.profile.height_cm)
```

### Applying custom filtering before pagination
```python
repo = ExerciseSetLogRepository()
logs = repo.list_for_subject(
    subject_id=subject_id,
    date_from=date.today() - timedelta(days=7),
    date_to=date.today(),
    exercise_id=target_exercise_id,
    sort=["-performed_at", "-set_index"],
)
```
