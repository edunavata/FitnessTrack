Project fitness_track {
  database_type: "PostgreSQL"
  Note: 'RGPD-ready model. Subject pattern: domain entities point to subjects; users holds direct PII.'
}

// ================== Enums ==================
Enum muscle_group {
  CHEST
  BACK
  SHOULDERS
  QUADS
  HAMSTRINGS
  GLUTES
  CALVES
  BICEPS
  TRICEPS
  FOREARMS
  ABS
  OBLIQUES
  FULL_BODY
  OTHER
}

Enum equipment {
  BARBELL
  DUMBBELL
  MACHINE
  CABLE
  BODYWEIGHT
  KETTLEBELL
  BAND
  SMITH
  TRAP_BAR
  EZ_BAR
  PLATE
  OTHER
}

Enum mechanics {
  COMPOUND
  ISOLATION
}

Enum force_vector {
  PUSH
  PULL
  STATIC
}

Enum level {
  BEGINNER
  INTERMEDIATE
  ADVANCED
}

Enum movement_pattern {
  HINGE
  SQUAT
  LUNGE
  HORIZONTAL_PUSH
  HORIZONTAL_PULL
  VERTICAL_PUSH
  VERTICAL_PULL
  CARRY
  ROTATION
  ANTI_ROTATION
  HIP_ABDUCTION
  HIP_ADDUCTION
  CALF_RAISE
  CORE_BRACE
  OTHER
}

Enum sex {
  MALE
  FEMALE
  OTHER
  PREFER_NOT_TO_SAY
}

Enum workout_status {
  PENDING
  COMPLETED
}

// ================== Autenticación (PII directo) ==================
Table users {
  id             int [pk, increment]                      // surrogate PK
  email          varchar(254) [not null, unique]          // direct PII
  password_hash  varchar(128) [not null]
  username       varchar(50) [not null, unique]           // direct PII (alias)
  full_name      varchar(100)                             // direct PII (opcional)
  created_at     timestamptz [not null, default: `now()`]
  updated_at     timestamptz [not null, default: `now()`]

  Note: 'Authentication identity holding direct PII. No indirect PII here (weight, height, etc.).'
}

// ================== Subject Pattern ==================
Table subjects {
  id            int  [pk, increment]
  // vínculo a user (direct PII). En anonimización: set NULL y borra users.
  user_id       int  // nullable a propósito para permitir anonimización
  pseudonym     uuid [not null, unique, note: 'Stable pseudonymous ID']
  created_at    timestamptz [not null, default: `now()`]
  updated_at    timestamptz [not null, default: `now()`]

  indexes {
    user_id [unique, name: 'uq_subjects_user'] // 1:1 cuando user existe
  }

  Note: 'Pseudonymous subject. All domain records point here. Break link to users on anonymization (set NULL).'
}

// PII indirecto (perfil estático mínimamente identificable)
Table subject_profiles {
  id            int [pk, increment]
  subject_id    int [not null]
  sex           sex
  birth_year    int       // evita DOB exacta
  height_cm     int       // altura "base"
  // Otros metadatos de bajo riesgo (opcional)
  dominant_hand varchar(10)

  created_at    timestamptz [not null, default: `now()`]
  updated_at    timestamptz [not null, default: `now()`]

  indexes {
    subject_id [unique, name: 'uq_subject_profiles_subject'] // 1:1 perfil
  }

  Note: 'Indirect PII (static-ish). Height here, not in users. Keep minimal.'
}

// Métricas corporales (serie temporal) — opcional pero recomendable
Table subject_body_metrics {
  id              int [pk, increment]
  subject_id      int [not null]
  measured_on     date [not null]

  weight_kg       numeric(5,2)
  bodyfat_pct     numeric(4,1)
  resting_hr      int
  notes           text

  created_at      timestamptz [not null, default: `now()`]
  updated_at      timestamptz [not null, default: `now()`]

  indexes {
    (subject_id, measured_on) [unique, name: 'uq_sbm_subject_day']
  }

  Note: 'Time series of indirect PII (e.g., weight changes).'
}

// ================== Catálogo de ejercicios ==================
Table exercises {
  id                  int              [pk, increment]
  name                varchar(120)     [not null]
  slug                varchar(140)     [not null, unique]
  primary_muscle      muscle_group     [not null]
  movement            movement_pattern [not null]
  mechanics           mechanics        [not null]
  force               force_vector     [not null]
  unilateral          boolean          [not null, default: false]
  equipment           equipment        [not null]
  grip                varchar(50)
  range_of_motion     text
  difficulty          level            [not null, default: 'BEGINNER']
  cues                text
  instructions        text
  video_url           varchar(255)
  is_active           boolean          [not null, default: true]
  created_at          timestamptz      [not null, default: `now()`]
  updated_at          timestamptz      [not null, default: `now()`]

  indexes {
    name [name: 'ix_exercises_name']
  }

  Note: 'Exercise catalog with biomechanical metadata.'
}

Table exercise_aliases {
  id           int [pk, increment]
  exercise_id  int [not null]
  alias        varchar(120) [not null]

  indexes {
    (exercise_id, alias) [unique, name: 'uq_exercise_alias']
  }

  Note: 'Alternative/common names for exercises.'
}

Table tags {
  id     int [pk, increment]
  name   varchar(50) [not null, unique]
  Note: 'Free-form but curated tags.'
}

Table exercise_tags {
  exercise_id  int [not null]
  tag_id       int [not null]

  indexes {
    (exercise_id, tag_id) [unique, name: 'uq_exercise_tag']
  }
}

Table exercise_secondary_muscles {
  exercise_id   int [not null]
  muscle        muscle_group [not null]

  indexes {
    (exercise_id, muscle) [unique, name: 'uq_exercise_muscle']
  }

  Note: 'Normalized N:M for secondary muscles.'
}

// ================== Rutinas (plantilla/plan) ==================
Table routines {
  id                 int [pk, increment]
  subject_id         int [not null]  // RGPD: ya no apunta a users
  name               varchar(120) [not null]
  description        text
  starts_on          date
  is_active          boolean [not null, default: true]
  created_at         timestamptz [not null, default: `now()`]
  updated_at         timestamptz [not null, default: `now()`]

  indexes {
    (subject_id, is_active) [name: 'ix_routines_subject_active']
    (subject_id, name)      [unique, name: 'uq_routines_subject_name']
  }

  Note: 'Mesocycle template (per subject).'
}

Table routine_days {
  id          int           [pk, increment]
  routine_id  int           [not null]
  day_index   int           [not null, note: '1..cycle length']
  is_rest     boolean       [not null, default: false]
  title       varchar(100)
  notes       text
  created_at  timestamptz   [not null, default: `now()`]
  updated_at  timestamptz   [not null, default: `now()`]

  indexes {
    (routine_id, day_index) [unique, name: 'uq_routine_days_routine_day_index']
  }

  Note: 'Specific day in the cycle template.'
}

Table routine_day_exercises {
  id              int           [pk, increment]
  routine_day_id  int           [not null]
  exercise_id     int           [not null]
  position        int           [not null, note: '1..N order']
  notes           text
  created_at      timestamptz   [not null, default: `now()`]
  updated_at      timestamptz   [not null, default: `now()`]

  indexes {
    (routine_day_id, position)     [unique, name: 'uq_rde_day_pos']
    (routine_day_id, exercise_id)  [name: 'ix_rde_day_exercise']
  }

  Note: 'Exercise sequence for a template day.'
}

Table routine_exercise_sets {
  id                         int           [pk, increment]
  routine_day_exercise_id    int           [not null]
  set_index                  int           [not null, note: '1..N order within exercise/day']
  is_warmup                  boolean       [not null, default: false]
  to_failure                 boolean       [not null, default: false]

  // Planned targets
  target_weight_kg           numeric(6,2)
  target_reps                int
  target_rir                 int
  target_rpe                 numeric(3,1)
  target_tempo               varchar(15)
  target_rest_s              int

  notes                      text
  created_at                 timestamptz   [not null, default: `now()`]
  updated_at                 timestamptz   [not null, default: `now()`]

  indexes {
    (routine_day_exercise_id, set_index) [unique, name: 'uq_res_rde_set_idx']
  }

  Note: 'Planned set targets.'
}

// ================== Ejecución (ciclos/sesiones/logs) ==================
Table cycles {
  id           int [pk, increment]
  subject_id   int [not null] // RGPD: reemplaza user_id
  routine_id   int [not null]
  cycle_number int [not null, note: 'Sequential per routine (1..N)']

  started_on   date
  ended_on     date
  notes        text

  created_at   timestamptz [not null, default: `now()`]
  updated_at   timestamptz [not null, default: `now()`]

  indexes {
    (routine_id, cycle_number) [unique, name: 'uq_cycles_routine_number']
    (subject_id, started_on)   [name: 'ix_cycles_subject_started_on']
    routine_id                 [name: 'ix_cycles_routine']
  }

  Note: 'Execution instance of a routine (subject pass-through).'
}

Table workout_sessions {
  id                int            [pk, increment]
  subject_id        int            [not null] // RGPD: reemplaza user_id
  workout_date      date           [not null]
  status            workout_status [not null, default: 'PENDING']

  routine_day_id    int            // optional: link to planned day
  cycle_id          int            // optional: link to cycle instance

  location          varchar(120)
  perceived_fatigue int
  bodyweight_kg     numeric(5,2)
  notes             text
  created_at        timestamptz    [not null, default: `now()`]
  updated_at        timestamptz    [not null, default: `now()`]

  indexes {
    (subject_id, workout_date) [unique, name: 'uq_ws_subject_date']
    routine_day_id             [name: 'ix_ws_routine_day']
    cycle_id                   [name: 'ix_ws_cycle']
  }

  Note: 'Session grouped by day; may link to routine day and/or cycle.'
}

Table exercise_set_logs {
  id                   int            [pk, increment]

  subject_id           int            [not null] // RGPD: reemplaza user_id
  exercise_id          int            [not null]
  session_id           int            // optional
  planned_set_id       int            // optional (adherence analytics)

  performed_at         timestamptz    [not null]
  set_index            int            [not null]
  is_warmup            boolean        [not null, default: false]
  to_failure           boolean        [not null, default: false]

  actual_weight_kg     numeric(6,2)
  actual_reps          int
  actual_rir           int
  actual_rpe           numeric(3,1)
  actual_tempo         varchar(15)
  actual_rest_s        int

  notes                text
  created_at           timestamptz    [not null, default: `now()`]
  updated_at           timestamptz    [not null, default: `now()`]

  indexes {
    (subject_id, performed_at)                         [name: 'ix_esl_subject_time']
    (exercise_id, performed_at)                        [name: 'ix_esl_exercise_time']
    (subject_id, exercise_id, performed_at, set_index) [unique, name: 'uq_esl_session_set']
    (subject_id, exercise_id, session_id, set_index)   [name: 'ix_esl_by_session']
    planned_set_id                                     [name: 'ix_esl_planned']
  }

  Note: 'Per-set execution log. Links optionally to planned set and session.'
}

// ================== Foreign Keys (solo Ref:) ==================
Ref: subjects.user_id > users.id [delete: set null]

Ref: subject_profiles.subject_id > subjects.id [delete: cascade]
Ref: subject_body_metrics.subject_id > subjects.id [delete: cascade]

Ref: exercise_aliases.exercise_id > exercises.id [delete: cascade]
Ref: exercise_tags.exercise_id > exercises.id [delete: cascade]
Ref: exercise_tags.tag_id > tags.id [delete: cascade]
Ref: exercise_secondary_muscles.exercise_id > exercises.id [delete: cascade]

Ref: routines.subject_id > subjects.id [delete: cascade]
Ref: routine_days.routine_id > routines.id [delete: cascade]
Ref: routine_day_exercises.routine_day_id > routine_days.id [delete: cascade]
Ref: routine_day_exercises.exercise_id > exercises.id
Ref: routine_exercise_sets.routine_day_exercise_id > routine_day_exercises.id [delete: cascade]

Ref: cycles.subject_id > subjects.id [delete: cascade]
Ref: cycles.routine_id > routines.id [delete: cascade]

Ref: workout_sessions.subject_id > subjects.id [delete: cascade]
Ref: workout_sessions.routine_day_id > routine_days.id [delete: set null]
Ref: workout_sessions.cycle_id > cycles.id [delete: set null]

Ref: exercise_set_logs.subject_id > subjects.id [delete: cascade]
Ref: exercise_set_logs.exercise_id > exercises.id
Ref: exercise_set_logs.session_id > workout_sessions.id [delete: cascade]
Ref: exercise_set_logs.planned_set_id > routine_exercise_sets.id [delete: set null]
