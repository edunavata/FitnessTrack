Project fitness_track {
  database_type: "PostgreSQL"
  Note: 'Relational model for FitnessTrack. Plan (routines) vs Actuals (exercise_set_logs).'
}

Table users {
  id             int [pk, increment]                      // surrogate PK
  email          varchar(254) [not null, unique]          // login email
  password_hash  varchar(128) [not null]                  // hashed password
  username       varchar(50) [not null, unique]           // display or nickname
  full_name      varchar(100)                             // optional real name
  age            int [note: 'Optional, in years']         // optional for stats
  height_cm      int [note: 'Optional, height in cm']     // optional
  weight_kg      numeric(5,2) [note: 'Optional, weight']  // e.g., 85.50 kg
  created_at     timestamptz [not null, default: `now()`] // creation timestamp
  updated_at     timestamptz [not null, default: `now()`] // last update

  Note: 'Users table for fitness tracking app.'
}

// === Domain Enums ===
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

// === Exercises Catalog ===
Table exercises {
  id                  int              [pk, increment]                         // surrogate PK
  name                varchar(120)     [not null]                              // display name
  slug                varchar(140)     [not null, unique]                      // URL-safe, unique (global)
  primary_muscle      muscle_group     [not null]                              // main target
  movement            movement_pattern [not null]                              // movement taxonomy
  mechanics           mechanics        [not null]                              // compound/isolation
  force               force_vector     [not null]                              // push/pull/static
  unilateral          boolean          [not null, default: false]              // single-limb?
  equipment           equipment        [not null]                              // primary equipment
  grip                varchar(50)                                              // e.g., neutral, supinated
  range_of_motion     text                                                     // ROM notes
  difficulty          level            [not null, default: 'BEGINNER']         // skill level
  cues                text                                                     // coaching cues
  instructions        text                                                     // step-by-step guide
  video_url           varchar(255)                                             // optional reference
  is_active           boolean          [not null, default: true]               // soft availability
  created_at          timestamptz      [not null, default: `now()`]
  updated_at          timestamptz      [not null, default: `now()`]

  indexes {
    name [name: 'ix_exercises_name']  // helpful search by name; uniqueness via slug
  }

  Note: 'Catalog of exercises with biomechanical metadata for hypertrophy planning.'
}

// Optional normalization for aliases (búsquedas y localismos)
Table exercise_aliases {
  id           int [pk, increment]
  exercise_id  int [not null, ref: > exercises.id, note: 'Alias belongs to an exercise']
  alias        varchar(120) [not null]

  indexes {
    (exercise_id, alias) [unique, name: 'uq_exercise_alias']
  }

  Note: 'Common alternative names, e.g., "Hip Thrust" ~ "Puente de glúteo".'
}

// Optional tags (robusto para búsqueda/filtrado sin proliferar enums)
Table tags {
  id     int [pk, increment]
  name   varchar(50) [not null, unique]
  Note: 'Free-form but curated tags (e.g., POWERLIFTING, MOBILITY, TEMPO_EMPHASIS).'
}

Table exercise_tags {
  exercise_id  int [not null, ref: > exercises.id]
  tag_id       int [not null, ref: > tags.id]

  indexes {
    (exercise_id, tag_id) [unique, name: 'uq_exercise_tag']
  }
}

// ========= ROUTINES = MESOCYCLES =========
Table routines {
  id                 int [pk, increment]
  user_id            int [not null, ref: > users.id]  // [delete: cascade] applied below in refs
  name               varchar(120) [not null]
  description        text
  starts_on          date
  is_active          boolean [not null, default: true]
  created_at         timestamptz [not null, default: `now()`]
  updated_at         timestamptz [not null, default: `now()`]

  indexes {
    (user_id, is_active) [name: 'ix_routines_user_active']
    (user_id, name) [unique, name: 'uq_routines_user_name'] // evita nombres duplicados por usuario
  }

  Note: 'Mesocycle template (per user). Consider 1 active routine per user as policy, not constraint.'
}

// === Day slots within a routine cycle ===
Table routine_days {
  id          int           [pk, increment]
  routine_id  int           [not null, ref: > routines.id]
  day_index   int           [not null, note: '1..cycle_length_days']
  is_rest     boolean       [not null, default: false]
  title       varchar(100)                           // e.g., Push / Pull / Legs / Rest
  notes       text
  created_at  timestamptz   [not null, default: `now()`]
  updated_at  timestamptz   [not null, default: `now()`]

  indexes {
    (routine_id, day_index) [unique, name: 'uq_routine_days_routine_day_index']
  }

  Note: 'Represents a specific day in the cycle; can be a rest day.'
}

// === Ordered exercise list for a given routine day ===
Table routine_day_exercises {
  id              int           [pk, increment]
  routine_day_id  int           [not null, ref: > routine_days.id]
  exercise_id     int           [not null, ref: > exercises.id]
  position        int           [not null, note: '1..N order within the day']
  notes           text
  created_at      timestamptz   [not null, default: `now()`]
  updated_at      timestamptz   [not null, default: `now()`]

  indexes {
    (routine_day_id, position)     [unique, name: 'uq_rde_day_pos']
    (routine_day_id, exercise_id)  [name: 'ix_rde_day_exercise']
  }

  Note: 'Exercise sequence for the day; number of sets comes from routine_exercise_sets.'
}

// === Planned sets per routine-day-exercise (1:N) ===
Table routine_exercise_sets {
  id                         int           [pk, increment]
  routine_day_exercise_id    int           [not null, ref: > routine_day_exercises.id]
  set_index                  int           [not null, note: '1..N order for this exercise on this day']
  is_warmup                  boolean       [not null, default: false]
  to_failure                 boolean       [not null, default: false]
  // ---- Targets (planned) ----
  target_weight_kg           numeric(6,2)  // planned load in kg
  target_reps                int           // planned reps
  target_rir                 int           // planned reps-in-reserve (suggest 0..6)
  target_rpe                 numeric(3,1)  // planned RPE (e.g., 6.0..10.0)
  target_tempo               varchar(15)   // e.g., '3-1-1-0'
  target_rest_s              int           // planned rest (seconds)

  notes                      text
  created_at                 timestamptz   [not null, default: `now()`]
  updated_at                 timestamptz   [not null, default: `now()`]

  indexes {
    (routine_day_exercise_id, set_index) [unique, name: 'uq_res_rde_set_idx']
  }

  Note: 'Planned targets per set in the routine. Exact scheme (reps/RIR/RPE/kg/tempo/rest).'
}

// === Status enum for workout sessions ===
Enum workout_status {
  PENDING
  COMPLETED
}

// === Execution logs (actuals), opcionalmente vinculables al plan ===
// PATCH: add optional linkage from workout_sessions -> routine_days
Table workout_sessions {
  id                int            [pk, increment]
  user_id           int            [not null, ref: > users.id]
  workout_date      date           [not null, note: 'Day when the workout took place']
  status            workout_status [not null, default: 'PENDING']

  // NEW: optional linkage to planned routine day
  routine_day_id    int            [ref: > routine_days.id, note: 'Optional: session planned under this routine day']

  location          varchar(120)
  perceived_fatigue int
  bodyweight_kg     numeric(5,2)
  notes             text
  created_at        timestamptz    [not null, default: `now()`]
  updated_at        timestamptz    [not null, default: `now()`]

  indexes {
    (user_id, workout_date) [unique, name: 'uq_ws_user_date'] // keep 1 session/day per user (adjust if needed)
    routine_day_id          [name: 'ix_ws_routine_day']
  }

  Note: 'Workout session grouped by training day. Optionally linked to a routine day to track planned origin.'
}


// Logs por set (con enlace opcional al set planificado)
Table exercise_set_logs {
  id                   int            [pk, increment]

  // Who and what
  user_id              int            [not null, ref: > users.id]
  exercise_id          int            [not null, ref: > exercises.id]
  session_id           int            [ref: > workout_sessions.id, note: 'Optional link to a workout session']
  planned_set_id       int            [ref: > routine_exercise_sets.id, note: 'Optional link to planned set']

  // Session timing & ordering
  performed_at         timestamptz    [not null, note: 'When the set was performed']
  set_index            int            [not null, note: '1..N order within the exercise for this session']
  is_warmup            boolean        [not null, default: false]
  to_failure           boolean        [not null, default: false]

  // ---- Actuals (performed) ----
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
    (user_id, performed_at)                         [name: 'ix_esl_user_time']
    (exercise_id, performed_at)                     [name: 'ix_esl_exercise_time']
    (user_id, exercise_id, performed_at, set_index) [unique, name: 'uq_esl_session_set'] // evita duplicados
    (user_id, exercise_id, session_id, set_index)   [name: 'ix_esl_by_session']           // lecturas por sesión
    (planned_set_id)                                [name: 'ix_esl_planned']              // análisis adherencia
  }

  Note: 'Per-set execution log (actuals). planned_set_id permite métricas de adherencia sin forzar el enlace.'
}

// Optional: N:M para músculos secundarios normalizados
Table exercise_secondary_muscles {
  exercise_id   int [not null, ref: > exercises.id]
  muscle        muscle_group [not null]

  indexes {
    (exercise_id, muscle) [unique, name: 'uq_exercise_muscle']
  }

  Note: 'Normalized mapping for secondary muscles (replaces CSV).'
}



Ref: "routine_days"."id" < "routine_days"."title"
