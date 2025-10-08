# FitnessTrack — Diseño de Servicios (CQRS-light, resumen esencial)

## 1) Regla base
- **DTOs** solo en **API ⇄ Services**.
- **Services** orquestan **UoW** (transacciones), autorizan y coordinan repos.
- **Repos** = persistencia pura (sin lógica de caso de uso).

## 2) Tipos de servicio (cómo decidimos)
- **Aggregate (A):** opera sobre **un agregado** y sus invariantes locales.
- **Process/Workflow (P):** coordina **2+ agregados** con **atomicidad** / side-effects / idempotencia.
- **Query (Q):** **solo lectura** y proyecciones (sin mutar).

> Regla rápida: 1 agregado → **A**.
> 2+ agregados con “todo-o-nada” → **P**.
> Solo lectura → **Q**.

## 3) Inventario y justificación (por la lógica A/P/Q)

| Servicio | Tipo | Justificación (por qué cae en A/P/Q) | Repos clave |
|---|---|---|---|
| **IdentityService** | A | Gestiona **User** (PII, password, roles). No cruza agregados; invariantes de cuenta. Tokens fuera. | `users` |
| **AuthService** | A | Ciclo de **autenticación** (login/refresh/logout). Opera sobre tokens/sesiones de User; no coordina otros agregados del dominio. | `users` (tokens/sesiones) |
| **SubjectService** | A | Gestiona **Subject** (perfil, vínculo/desvínculo con User). Invariantes del sujeto; no necesita mutar otros agregados. | `subjects` |
| **SubjectMetricsService** | A | **Series 1:N** de métricas del Subject. Un agregado propio por volumen/patrón de acceso; no cruza agregados. | `subject_body_metrics` |
| **SavedRoutineService** | A | **Asociación** subject↔routine (guardar/quitar). Inserta relación idempotente; no muta `Subject` ni `Routine`. | `saved_routines`, `routines` |
| **UserRegistrationService** | **P** | **Registro** crea **User + Subject** y enlaza en **una transacción**; requiere **idempotencia** y posibles side-effects. | `users`, `subjects` |
| **IdentityQueryService** | Q | Lecturas de User (paginación/filters). No muta estado. | `users` |
| **SubjectQueryService** | Q | Lecturas/proyecciones de Subject. No muta estado. | `subjects` |
| **ProgressReportService** | Q | Lecturas compuestas (volumen, PRs). Varias consultas requieren snapshot consistente. | `workouts`, `exercises` |

## 4) Políticas por tipo (transacciones y concurrencia)
- **A (Aggregate):** UoW **RW**; `update/delete` con **ETag (If-Match→412)**; `get_for_update` solo si hay contención real.
- **P (Process):** UoW **RW multi-repo**; **Idempotency-Key** en endpoints reintentables; “todo-o-nada” + side-effects controlados.
- **Q (Query):** UoW **RO**; **READ COMMITTED** por defecto; **REPEATABLE READ** para informes/snapshots multi-consulta.

## 5) Heurística de decisión (siempre igual)
- **¿Toca 1 agregado y nada más?** → **Aggregate**.
- **¿Toca 2+ agregados y debe confirmarse junto?** → **Process**.
- **¿Solo lees/proyectas?** → **Query**.
- **Duda:** empieza en Aggregate y **extrae** a Process si aparecen atomicidad, idempotencia o side-effects cruzando agregados.
