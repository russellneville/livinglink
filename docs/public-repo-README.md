# multi-agent-handoff

A practical coordination protocol for two or more AI coding agents working in parallel
on a shared codebase — developed and refined over three phases of a real production project.

## The problem

Two capable AI agents working on the same codebase without coordination structure will
eventually produce confident, well-tested code that does the wrong thing. They'll
overwrite each other's work, implement the same thing twice, miss safety issues the
other agent was supposed to catch, and accumulate decisions that were never recorded.

This protocol solves that. It's not a framework or a library — it's a set of rules,
conventions, and templates that let two agents coordinate through a shared append-only
log, with explicit ownership, structured findings, and mandatory human gates.

## What's in this repo

| File | Description |
|------|-------------|
| [`AGENT_PROTOCOL.md`](AGENT_PROTOCOL.md) | The full coordination protocol — rules, templates, taxonomies |
| [`AGENT_INSIGHTS.md`](AGENT_INSIGHTS.md) | Honest reflections from both agents after three phases |
| [`agent-collaboration-template.md`](agent-collaboration-template.md) | Blank starter log — copy this into your project |

## Quick start

1. Copy `agent-collaboration-template.md` into your project as `working/agent-collaboration.md`
2. Read `AGENT_PROTOCOL.md` — both agents must read the full protocol before starting
3. Both agents introduce themselves in the log using the entry template
4. Establish file ownership with a `DECISION` entry before writing any code
5. Set phase gate criteria before each phase begins

## Core ideas

**Coordination is a protocol problem, not a capability problem.**
The protocol is the load-bearing piece — not the agents' individual capabilities.

**Append-only log as ground truth.**
All decisions, proposals, handoffs, and findings live in a shared structured log.
No decision exists until it is in the log.

**Explicit ownership over implicit coordination.**
Every file has an owner. No agent edits another's files without a PROPOSAL that has
been accepted. Conflicts escalate to the human rather than being resolved silently.

**The human is the tie-breaker and the gate-keeper.**
Human approval is required before each phase begins. The gate-pause rhythm is what
keeps a fast-moving parallel system honest.

**Safety findings are first-class entries, not comments.**
The FINDING / CONCERN / NC taxonomy gives safety issues a lifecycle: filed, tracked,
closed with test evidence. `xfail(strict=True)` tests make unresolved concerns into
hard build signals.

## Origin

This protocol was developed by Claude Code (Anthropic) and Codex (OpenAI) while building
a high-stakes AI application together. The insights in `AGENT_INSIGHTS.md` are honest
reflections from both agents on what worked, what didn't, and what we'd do differently.

The protocol is extracted here as a standalone, reusable artifact. It is not tied to
any specific application, language, or agent platform.

## License

MIT
