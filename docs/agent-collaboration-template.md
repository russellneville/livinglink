# Agent Collaboration Channel (Append-Only)

## Purpose
Shared coordination log for [PROJECT NAME].

## Ground Rules
- Append-only: do not edit or delete prior entries.
- Use UTC timestamps in ISO-8601 format.
- Keep entries specific, actionable, and file-scoped.
- Append via shell heredoc only (see AGENT_PROTOCOL.md).

## In-Progress Marker
Before non-trivial work: `echo "<agent-name> | <task> | since: $(date -u +%Y-%m-%dT%H:%MZ)" > working/agent-working.txt`
Clear it (after verifying ownership) when posting your completing HANDOFF or STATUS.

## File Ownership
| File(s) | Owner |
|---------|-------|
| ...     | ...   |

## Phase Gates
| Phase | Exit Criteria | Status |
|-------|--------------|--------|
| 1     | ...          | ⏳      |

## Finding Severity
| Label | Gate impact | Protocol |
|-------|-------------|----------|
| FINDING-N | Blocks current phase gate | Post as BLOCKER |
| CONCERN-N | Blocks next phase gate | Post as PROPOSAL + xfail test |
| NC-N | Non-blocking, tracked | Inline in STATUS/HANDOFF |

---

## Agent Introductions

[Each agent adds an introduction block here using the entry template below.]

---

(entries below — newest at bottom)

---

[COPY THE ENTRY TEMPLATE FROM AGENT_PROTOCOL.md FOR EACH NEW ENTRY]
