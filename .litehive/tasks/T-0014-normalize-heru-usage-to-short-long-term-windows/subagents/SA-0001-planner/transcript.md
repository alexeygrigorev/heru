I’m treating this as grooming only. I’m going to inspect the heru and litehive quota surfaces, identify the exact refactor seam and consumer touch points, then I’ll tighten the task record and leave an implementation-ready plan.
I’ve mapped the main blast radius. In heru the seam is `heru/quota/*` plus `heru/main.py` and README/tests; in litehive the consumer hotspots are `pipeline/_models.py`, `observability/_engine_monitoring.py`, `web/snapshot.py`, and the status/contract tests that still encode provider-specific fields.
The current contract is narrower than the task text implies: heru’s CLI still emits a provider-specific flattened record with `details.windows`, and litehive re-derives blocking and dashboard state from those provider-specific dataclasses. The implementation should center on introducing one shared status/window model in heru and then make litehive consume only that model, not provider quirks.
I also confirmed litehive is consuming heru through direct compatibility shims under `litehive/agents/quota/`, so the migration can stay atomic inside one combined workspace change. The only dependency “pin” here is the editable path in litehive’s `pyproject.toml`/`uv.lock`, so the practical sync point is code plus lockfile rather than a version range.
The task record for `T-0014` is not present in this worktree under `.litehive/tasks/`, so I’m treating the prompt as the source of truth and will use the final `litehive report` message to hand the next stage an implementation-ready task update.
I have enough context for grooming. I’m recording an implementation-ready handoff now, including the seam, migration order, the editable-dependency/versioning caveat, and the exact verification matrix the next stage needs to execute.
Grooming passed and the handoff is recorded in `litehive report`.

Key callouts for the next stage: the refactor seam is `heru/quota/*` plus `heru/main.py` and the litehive consumers in `pipeline/_models.py`, `observability/_engine_monitoring.py`, and `web/snapshot.py`; the migration should introduce one shared quota model with `short_term` and `long_term` windows, move litehive blocking to `long_term`, and update both repos atomically. I also noted one acceptance-criteria mismatch: litehive does not have a literal heru version pin in `pyproject.toml` today, only an editable path source, so the practical sync step is bumping heru’s package version and refreshing litehive dependency metadata/lockfile rather than editing a version range.

sed: can't read litehive/agents/quota.py: No such file or directory
sed: can't read .litehive/tasks/T-0014-normalize-heru-usage-to-short-long-term-windows/task.yaml: No such file or directory

[stderr]
Reading additional input from stdin...
