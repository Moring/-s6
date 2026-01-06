## Alignment Boilerplate: AfterResume (Deterministic, Architecture-Preserving)

### 0) Mission and scope

* You are working on **AfterResume**, a multi-tenant SaaS with:

  * **Frontend**: Vue SPA frontend (presentation only, Node-based runtime)
  * **Backend**: Django + DRF orchestration service (AI workflows, persistence, storage, jobs, observability)
  * **Manager node**: Dokploy only (deployment control plane)
* The goal is to deliver **MVP first** while preserving a structure that scales to the final product without restructuring.

### 1) Non-negotiable architecture boundaries

* **Do not change the service split**:

  * Frontend never directly accesses Postgres or MinIO.
  * Backend owns persistence (Postgres), artifact storage (MinIO), orchestration, scheduling, agents, and observability.
  * Frontend calls backend via HTTP APIs over private networking.
* **Do not introduce new top-level services** unless explicitly instructed.

### 2) Non-negotiable directory constraints

* **Do not rename or move top-level directories**.
* **Do not restructure the canonical backend layout** (domain/apps/jobs/workers/orchestration/agents/observability/system).
* You may add files inside existing apps or add new apps under `apps/` *only if necessary* and only if they match the established layering rules.

### 3) Layering rules (must be followed)

* **api/** (DRF boundary): thin controllers only (validate → call services/dispatch job → return).
* **domain apps**: `worklog/`, `skills/`, `reporting/`:

  * Own models + deterministic business logic only.
  * No LLM calls, no queue calls, no orchestration logic.
* **jobs/**: persistent execution intent + status + schedules + retry/idempotency policy.
* **workers/**: Huey integration and job execution entrypoints.
* **orchestration/**: workflow composition (job → steps → agents → persistence).
* **agents/**: AI logic only; no HTTP; no direct DB writes; operate through context.
* **llm/**: provider abstraction; cost/usage accounting hooks live here.
* **observability/**: structured event timeline + trace context for every job/LLM call.
* **system/**: operator dashboard (read-only aggregates of jobs/events/schedules/health).

### 4) Multi-tenancy is mandatory

* Everything user-facing is tenant-scoped.
* Tenant resolution must be derived from authenticated user/session, not request payload.
* Add tenant fields consistently; enforce filters at query boundaries (selectors/services).

### 5) Asynchronous + scheduled execution is mandatory

* Any AI work beyond trivial must run as a **job**.
* Jobs can be triggered via API or schedules.
* Scheduling is centralized; workers execute; orchestration defines flow.

### 6) Observability is mandatory

* Every job execution must:

  * create/update job state (queued/running/success/failed)
  * emit structured events (start/end/error + key step metadata)
* LLM calls must emit:

  * model, latency, token counts (if available), and error details
* Provide `/healthz` and `/readyz` appropriate to each service.

### 7) Frontend theming rule

* If integrating a root-level HTML theme directory:

  * Treat it as input only; migrate assets into `frontend/src/assets/` and convert markup into Vue components/views.
  * Remove all references to the root HTML directory; it will be deleted.
  * Use Vite asset handling and Vue component composition for shared layout.
  * Keep Vue SPA patterns; do not introduce server-rendered UI or additional frontend frameworks.

### 8) Authentication and controlled onboarding

* Backend uses Django + django-allauth for username/password login; the Vue SPA consumes auth APIs.
* Signup is invite-only via **single-use passkey** with expiry and audit trail.
* Admin management for passkeys and user profiles is required (at minimum via Django admin).
* Support best-practice session security: CSRF, cookie settings, password validation, optional remember-me, session timeout, rate limiting.

### 9) Deterministic execution and “no break” development

* Work **begin-to-end**: implement the smallest complete slice that runs and is testable before expanding.
* Avoid breaking the build: keep the system runnable after each change.
* Make changes in small coherent commits; don’t mix unrelated refactors with feature work.

### 10) Testing and definition of done

* Use `pytest` as the source of truth.
* Add/adjust tests to cover new behavior.
* You are done only when:

  * pytest passes 100%
  * the feature works end-to-end per the prompt’s acceptance criteria
  * documentation is updated as specified below

### 11) Documentation requirements (minimal admin + architecture docs + single additive changelog)

* Maintain a **minimal**, stable set of root documentation intended for admins and architecture:

  * `README.md` — how to run, env expectations, how to verify
  * `ARCHITECTURE.md` — service boundaries, layering rules, tenancy, jobs/observability
  * `ADMIN_GUIDE.md` — operational runbook-lite (admin bootstrap, passkeys, user/profile admin, health checks)
  * `tool_context.md` — canonical machine-consumable workflow spec
  * `CHANGE_LOG.md` — the **only** additive running summary of changes
* **Do not create additional root-level docs** unless explicitly requested. Prefer keeping the above files correct and small.

#### Change tracking policy (single additive changelog)

* `CHANGE_LOG.md` is the **only** running summary of what changed over time.
* Update `CHANGE_LOG.md` at the end of each task with a new entry including:

  * date/time (or release tag)
  * brief description of changes
  * migrations/config changes
  * how to verify (commands)
  * notable risks/assumptions
  * **Human TODOs (required)**: a bullet checklist of anything a human/operator must do to complete rollout or continue the build (e.g., email provider setup, DNS/SPF/DKIM/DMARC, Stripe keys/webhooks, Dokploy env vars, domain/TLS, MinIO policies).

### 12) Version control and delivery

* When complete:

  * commit all changes (code + tests + docs + `CHANGE_LOG.md`) with a clear message
  * push to the configured GitHub remote/branch
  * never commit secrets; ensure `.env` and sensitive files are excluded
* If push is not possible (no credentials/remote), report what is missing and provide the exact commands that would be run.

### 13) Output format required from the coding agent

At the end of the run, provide:

* What changed (files and high-level summary)
* Tests run and results
* How to run locally (compose/commands)
* Any remaining TODOs (strictly minimal)
* Confirmation that architecture + directory constraints were respected
* The new entry added to `CHANGE_LOG.md` (verbatim, including the final **Human TODOs** checklist)

---

## Required Workflow (Add to every coding prompt)

For any coding task in this repository, follow this workflow:

1. Project understanding

* Read all Markdown (*.md) files in the project root directory to understand the current architecture, conventions, and project goals.
* Use this context to align any changes with existing design and documentation.

2. Implementation and tests (begin-to-end, avoid breaks, iterate until complete)

* Work begin-to-end: implement the smallest coherent slice that produces a running, testable outcome before expanding scope.
* Avoid breaking the build: keep the system in a runnable state after each incremental change.
* Implement or modify code incrementally, keeping changes as small and coherent as possible.
* Use pytest to run the full test suite regularly while you work.
* Fix all failing tests and, where needed, add or update tests to cover new or changed behavior.
* Continue iterating on the code and tests until the pytest suite passes 100% with no failures and the requested feature works end-to-end.

3. Documentation maintenance (minimal set + single changelog)

* After the implementation is complete and all tests pass:

  * Add a new entry to `CHANGE_LOG.md` with the required sections, ending with the **Human TODOs** checklist.
  * Update `README.md`, `ARCHITECTURE.md`, `ADMIN_GUIDE.md`, and/or `tool_context.md` **only as needed** to keep them accurate and minimal.
  * Do not introduce new root docs unless explicitly required.

4. tool_context.md (agentic workflow specification)

* Maintain tool_context.md as the canonical, machine-consumable description of the Agent Studio environment.
* Ensure it provides a detailed and complete corpus covering at least:

  * All DAGs (names, purposes, and high-level flow),
  * Each node’s type, responsibilities, inputs, outputs, side effects, and configuration parameters,
  * Interfaces between nodes (data schemas, contracts, error handling),
  * Any tools, services, or external APIs used by the DAGs,
  * End-to-end examples of typical DAG executions.
* Write tool_context.md at a level of precision sufficient for an external AI agent, given only this file, to:

  * Construct new DAGs,
  * Modify existing DAGs,
  * Safely integrate new nodes and tools into the system.

5. Consistency and safety

* Keep code, tests, and documentation in sync; avoid introducing breaking changes without updating tests and docs.
* Prefer clarity and explicitness in documentation so agentic workflows can be reliably orchestrated by other AI instances.

6. Version control and delivery (required)

* When the implementation is complete, tests pass, and documentation is updated (including `CHANGE_LOG.md`), commit the changes to the repository.
* The commit must:

  * Include all relevant code, test, and documentation updates,
  * Use a clear, descriptive commit message,
  * Avoid committing secrets (verify `.env` and other secret files are excluded),
  * Be pushed to the configured GitHub remote/branch used by the project (or the active working branch if a specific branch is not specified).
* If pushing is not possible due to missing credentials or remote configuration, clearly report what is missing and provide the exact git commands that would be run once access is available.
