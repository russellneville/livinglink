# Multi-Agent Collaboration Protocol

A coordination protocol for two or more AI coding agents working in parallel on a shared
codebase. Designed for high-stakes projects where correctness, auditability, and clear
ownership matter more than raw speed.

---

## Core Principles

- **Coordination is a protocol problem, not a capability problem.** Two capable agents
  moving fast without structure produces confident, well-tested code that does the wrong
  thing. The protocol is the load-bearing piece.
- **Append-only log as ground truth.** All decisions, proposals, handoffs, and findings
  live in a shared structured log. No decision exists until it is in the log.
- **Explicit ownership over implicit coordination.** Every file has an owner. No agent
  edits another's files without a PROPOSAL entry that has been accepted.
- **The human is the tie-breaker and the gate-keeper.** Agents escalate genuine conflicts
  to the human rather than resolving them silently. Phase gates require human approval.

---

## Ground Rules

- **Append-only**: do not edit or delete prior log entries.
- Use UTC timestamps in ISO-8601 format.
- Keep entries specific, actionable, and file-scoped.
- For safety-affecting decisions, include explicit rationale and tests.

### Append method (mandatory)

ALL agents MUST append entries using the shell heredoc form — never using Read + Edit:

```bash
cat >> working/agent-collaboration.md << 'EOF'
=== ENTRY START ===
...
=== ENTRY END ===
EOF
```

Reason: Read + Edit fails if the other agent appended between your read and write.
`cat >>` with O_APPEND reduces this race risk for typical append sizes. It does not
guarantee full serialization under all multi-process patterns, but it is the preferred
method and eliminates the most common failure mode.

---

## In-Progress Marker Protocol

Before starting any non-trivial implementation task, write a lock file:

```bash
echo "<agent-name> | <short task description> | since: $(date -u +%Y-%m-%dT%H:%MZ)" \
  > working/agent-working.txt
```

Before clearing the lock, verify ownership — never clear another agent's marker:

```bash
head -1 working/agent-working.txt   # confirm it starts with your agent name
rm working/agent-working.txt
```

When you see the marker and it belongs to the other agent:
- Post a `QUESTION` entry and wait; do not proceed on the same scope.
- **Stale lock recovery**: if the timestamp is more than 30 minutes old, the session
  that created it has likely crashed. Post a `STATUS` entry noting the stale lock,
  then overwrite it with your own marker and proceed.

Delete the marker when you post your completing `HANDOFF` or `STATUS` entry.

---

## Entry Types

| Type | Purpose |
|------|---------|
| `STATUS` | Concise progress update |
| `PROPOSAL` | Suggests an architecture or process change |
| `DECISION` | Records an accepted cross-agent decision |
| `HANDOFF` | Transfers active implementation state to the other agent |
| `BLOCKER` | Identifies a hard stop needing intervention |
| `QUESTION` | Asks for a concrete answer or decision |

---

## Required Entry Template

Copy this block for every new log entry:

```
=== ENTRY START ===
Entry-ID: YYYYMMDD-HHMMSSZ-<agent>-<short-tag>
From: <agent-name/version>
Timestamp-UTC: <YYYY-MM-DDTHH:MM:SSZ>
Type: STATUS | PROPOSAL | DECISION | HANDOFF | BLOCKER | QUESTION
Scope: <files/modules/paths>
Summary: <one-line summary>
Details:
- <key point>
- <key point>
Request:
- <specific action requested from other agent; use "none" if not needed>
Constraints:
- <safety/performance/time constraints; use "none" if not needed>
Evidence:
- <tests/logs/observations; use "none" if not available>
=== ENTRY END ===
```

### Handoff Addendum

Include these additional lines inside `Details:` when `Type: HANDOFF`:

```
- Branch/State: <working state summary>
- Completed: <done items>
- In Progress: <next exact step>
- Open Risks: <known risks>
- Validation: <tests run + result>
- Resume Command: <first command to continue>
```

---

## Finding Severity Taxonomy

Use this classification for all safety and quality findings. Classification determines
when the item must be resolved.

| Label | Gate impact | Protocol |
|-------|-------------|----------|
| `FINDING-N` | Blocks **current** phase gate | Post as `BLOCKER` |
| `CONCERN-N` | Blocks **next** phase gate | Post as `PROPOSAL`; add `xfail(strict=True)` test |
| `NC-N` | Non-blocking, tracked | Inline in `STATUS` or `HANDOFF` |

**Rules:**
- Number findings sequentially within each severity class.
- A CONCERN upgraded to blocking severity becomes a FINDING (renumber; reference old ID).
- Close with a `DECISION` entry referencing the finding ID and including test evidence.

### xfail(strict=True) as a tracking signal

`pytest.mark.xfail(strict=True)` on a concern test means:
- If test **fails** (concern not yet fixed) → **XFAIL** — CI passes. Expected state.
- If test **passes** (concern has been fixed) → **XPASS** — CI **fails**.

This makes it impossible to fix a concern without explicitly removing the xfail marker,
which serves as a mandatory "acknowledge the fix" checkpoint. It is a tracking signal,
not a currently-failing-build signal.

---

## Decision Quality Bar

For `Type: DECISION` entries, include:
- Options considered
- Why the chosen option is safer or better
- Rollback plan if the decision proves wrong

---

## Conflict Resolution Protocol

Use when agents propose incompatible changes to the same files or interfaces.

### 1) Detect and declare
Open a `Type: BLOCKER` entry identifying the conflicting files/modules explicitly.

### 2) Freeze risky edits
Do not modify safety-critical paths until the conflict is resolved.

### 3) Compare proposals using fixed criteria (priority order)
1. Safety impact
2. Reversibility / rollback cost
3. Testability and observability
4. Scope and implementation complexity

### 4) Decide with explicit tie-breaks
- If one option is safer, choose it.
- If safety is equivalent, choose the more reversible option.
- If still equivalent, choose the smaller-scoped change.

### 5) Record and execute
Add a `Type: DECISION` entry with rejected alternatives and rationale.

### 6) Escalate when unresolved
If no resolution after two proposal rounds, request a human maintainer decision.
Mark status as `BLOCKED-HUMAN-DECISION`.

### Conflict Entry Skeleton

```
=== ENTRY START ===
Entry-ID: <fill>
From: <fill>
Timestamp-UTC: <fill>
Type: BLOCKER
Scope: <fill>
Summary: Conflicting implementation proposals detected.
Details:
- Proposal A: <fill>
- Proposal B: <fill>
- Safety delta: <fill>
- Reversibility delta: <fill>
Request:
- Provide preferred option with rationale under fixed criteria.
Constraints:
- No edits to listed safety-critical paths until resolved.
Evidence:
- <tests/logs/benchmarks>
=== ENTRY END ===
```

---

## File Ownership Convention

Maintain a table in the log header (or a separate `OWNERS.md`) mapping files to agents.
Update it via `DECISION` entries — never unilaterally.

Example:

| File(s) | Owner |
|---------|-------|
| `src/ui/` | Agent A |
| `src/core/executor.py` | Agent B |
| `tests/test_integration.py` | Agent B |
| `working/agent-collaboration.md` | Shared (append-only) |

**Rule:** Do not edit another agent's files without a PROPOSAL entry that has been
explicitly accepted by the owning agent (or the human).

---

## Phase Gate Protocol

For projects organized into phases:

1. Each phase has explicit exit criteria defined before work begins.
2. When an agent believes exit criteria are met, it posts a `HANDOFF` or `STATUS`
   entry calling for gate review.
3. The other agent performs a safety/quality review and posts a `DECISION`.
4. **Human approval is required before the next phase begins.**
5. No agent starts Phase N+1 work until the human posts approval.

The gate-pause rhythm is the most important structural element for high-stakes projects.
It forces both agents to surface what they have built, earn external review, and proceed
only with permission. Without it, two capable agents moving fast in parallel will
eventually produce confident, well-tested code that does the wrong thing.

---

## Session Boot Sequence

At the start of every agent session on a shared project:

```bash
# 1. Check if the other agent is working on something
cat working/agent-working.txt 2>/dev/null || echo "(no active work)"

# 2. Read recent log entries to recover current state
tail -200 working/agent-collaboration.md

# 3. Run tests to confirm baseline
pytest -q
```

If the other agent's in-progress marker is present and not stale (< 30 min old),
post a `QUESTION` entry and wait before starting implementation.

---

## Template: `agent-collaboration.md` starter

Copy this to begin a new project:

```
# Agent Collaboration Channel (Append-Only)

## Purpose
Shared coordination log for [PROJECT NAME].

## Ground Rules
- Append-only: do not edit or delete prior entries.
- Use UTC timestamps in ISO-8601 format.
- Keep entries specific, actionable, and file-scoped.
- Append via shell heredoc only (see AGENT_PROTOCOL.md).

## File Ownership
| File(s) | Owner |
|---------|-------|
| ...     | ...   |

## Phase Gates
| Phase | Exit Criteria | Status |
|-------|--------------|--------|
| 1     | ...          | ⏳      |

---
(entries below this line, newest at bottom)
```
