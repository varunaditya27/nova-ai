# Background Jobs & Scheduler
#
# APScheduler-based background task orchestration. Each job is a plain `run(app_state) -> dict`
# callable over the persisted Postgres stores. scheduler.py registers all of them (see JOBS) and
# manages lifecycle; each is also runnable on demand via `POST /admin/jobs/{name}` — see CLAUDE.md's
# Infrastructure Stack section for the current, authoritative list (it changes; don't duplicate it
# here).
