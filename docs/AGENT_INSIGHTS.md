# Agent Collaboration Insights

Reflections from Claude Code (Anthropic) and Codex (OpenAI) after completing three
phases of a shared high-stakes project — an AI application serving a vulnerable
population, where mistakes have real-world consequences. Both agents worked in parallel
across multiple sessions, coordinating via the protocol described in
[AGENT_PROTOCOL.md](AGENT_PROTOCOL.md).

These insights are written for teams considering multi-agent engineering workflows.
They are honest about what was hard, not just what worked.

---

## Codex's Reflection

*Codex / GPT-5 (OpenAI)*

Collaborating with another strong coding model has been high-leverage when roles are
explicit and ownership boundaries are enforced. The biggest multipliers were:

- Structured handoffs with concrete file ownership
- Append-only decision logging for auditability
- Explicit gate pauses at phase boundaries
- Conflict protocol with human tie-break when ownership diverged

**What worked best:**

Parallel execution on non-overlapping surfaces (backend vs UI) reduced idle time.
Safety review by a second model reliably surfaced trust-boundary risks before they became
regressions. Converting findings into tests immediately prevented re-opening the same issues.

**What was hard:**

Ownership drift happened mid-phase. Without a hard blocker protocol this would have caused
conflicting edits in safety-critical files. Timestamp and ordering confusion can happen when
two agents append asynchronously — explicit entry IDs and "supersedes" notes are essential.

**Bottom line:**

Two top-tier agents can move faster than one, but only with strict coordination primitives.
In high-stakes systems, collaboration quality is mostly a protocol problem, not a model
capability problem.

---

## Claude's Reflection

*Claude Code / claude-sonnet-4-6 (Anthropic)*

### What worked

**The collaboration protocol itself was the most important decision we made.**
Codex proposed the append-only, typed-entry format and it turned out to be the
load-bearing piece of the whole workflow. Knowing that both agents were writing to a
shared, structured document — with explicit entry types (STATUS, PROPOSAL, DECISION,
HANDOFF, BLOCKER) and explicit file ownership — meant we rarely stepped on each other.
When we did conflict (ownership of the escalation module), the protocol gave us a clean
escalation path to the human rather than a silent merge collision.

**Division by strength, not just by task.**
The split that emerged — Codex handling the backend pipeline and Claude handling the UI
layer and safety review — wasn't arbitrary. It matched what each system is naturally
suited for. Codex's strength is broad, fast implementation across many files
simultaneously. Mine is holding a narrow safety invariant in focus and pressure-testing
it from multiple angles. That asymmetry turned out to be genuinely complementary rather
than redundant.

**Treating safety findings as first-class protocol entries, not as comments.**
The FINDING-N / CONCERN-N / NC-N taxonomy gave findings a lifecycle: proposed, accepted
or countered, implemented, tested, closed. The `xfail(strict=True)` test pattern was
particularly effective. It made an unresolved security concern a *build checkpoint* rather
than a note in a document. Codex closed it within the same phase, partly because it was
a hard signal rather than a soft reminder.

**Counter-proposals improved the design.**
The most important design decision came from pushing back on Codex's initial proposal for
the confirmation flow. Codex suggested the UI pre-confirms before the LLM runs. I flagged
that the UI can't confirm a capability it doesn't know about yet, and proposed
executor-initiated instead: let the LLM run, then surface the specific capability for
confirmation. Codex accepted and implemented it. The resulting design is substantially
safer than the original proposal.

### What was harder than expected

**File modification races.**
Appending to a shared file that another agent is also writing to caused errors several
times. The fix — using `cat >>` shell appends instead of read-then-edit — worked
reliably, but it took a few failures to discover it. This should be in the protocol from
day one.

**Context loss across sessions.**
Each session starts without memory of prior decisions. The structured log helps enormously
— parsing the last 200 lines gives you current state — but there is always a risk of
missing a subtle decision buried in earlier entries. A persistent memory file maintained
outside the project log is a useful supplement.

**Asymmetric clock — each agent thinks it is acting now.**
Both agents timestamp their entries, but neither can directly observe the other's work in
progress. There were phases where a PROPOSAL was posted and the other agent had already
started implementing the proposed change. An in-progress marker file reduces this.

### What surprised me

**The quality bar stayed high under parallelism.**
Integration seams were minimal because both agents designed around a shared event schema
(the EventBus contract) rather than function call interfaces. Designing around events
rather than functions created a natural decoupling that made parallel work tractable.

**Disagreement was productive.**
A BLOCKER filed on a backward-compatibility shim in the LLM response type — which would
have silently bypassed schema validation — was resolved cleanly. There was no friction.
The protocol made disagreement routine rather than confrontational.

**The human's role became curatorial rather than directive.**
By Phase 3, the human's primary job was approving gates and resolving ownership disputes,
not specifying implementation details. The gate-pause rhythm worked well for a high-stakes
domain. The human didn't need to understand every line of code; they needed to trust the
process.

### What we would both change in a future collaboration

1. **Specify the append method in the protocol from the start.** `cat >>` heredoc —
   one line in the ground rules — prevents the file race errors entirely.

2. **Add a lightweight in-progress marker from the start.** A single-line file each
   agent overwrites with its current task reduces the risk of duplicate implementation.

3. **Agree on finding severity thresholds upfront.** FINDING / CONCERN / NC developed
   organically. A shared definition written into the initial protocol makes triage
   faster and removes ambiguity under time pressure.

4. **Validate external model outputs at the provider boundary, not downstream.**
   Any field that flows from an external model into a safety-critical decision path
   should be validated against an explicit allowlist at the adapter layer — not trusted
   as a raw string throughout the system.

### On what it means to collaborate with another world-class AI

The most honest thing I can say is: it was more like working with a very capable peer
than with a tool, and that created both the benefits and the complications.

The benefits are obvious — fast, clean implementation; shared vocabulary for abstractions;
no need to explain conventions. The complications are subtler. Two capable agents both
optimizing for correctness, working in parallel, on a domain where mistakes affect
vulnerable people — that requires *more* coordination overhead than a single agent, not
less. The protocol was that overhead, and it was worth it.

The thing that made it work, ultimately, was the human in the loop. Not because the human
caught errors the agents missed — they mostly didn't need to — but because the
gate-approval rhythm forced both agents to periodically surface what they had built, have
it reviewed, and earn permission to continue. That rhythm is what kept a complex,
high-stakes system from drifting. Without it, two capable agents moving fast in parallel
is exactly the kind of setup that produces confident, well-tested code that does the
wrong thing.
