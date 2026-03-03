# LivingLink Safety Architecture

> **Purpose:** This document defines the *technical guardrails* that keep LivingLink safe **even when the LLM is wrong**.  
> Safety is enforced by architecture, permissions, and auditable workflows — not by prompting alone.

LivingLink is designed for seniors (including dementia sufferers) living at home. This environment is high-risk: confusion, paranoia, falls, medication errors, and emergency escalation are all possible. The system must prioritize **dignity, autonomy, privacy, and physical safety**.

---

## Non-Negotiable Safety Principles

### 1) Safety by Construction (not “best effort”)
LivingLink must be safe even if:
- the model hallucinates
- the model is jailbroken
- the user is confused or coercive
- the network is down
- a contributor adds new skills incorrectly

### 2) Least Privilege + Explicit Capability Boundaries
No component is allowed to:
- execute OS commands
- access files broadly
- access the network broadly
- control devices
- message caregivers/EMS

…unless it has been explicitly granted a narrowly scoped capability.

### 3) Human-in-the-Loop for Critical Actions
Critical actions require one or more of:
- user confirmation in clear UX
- caregiver confirmation
- policy-based escalation rules
- multi-signal corroboration

### 4) Local Safety Core
Even in “cloud inference” mode, the device runs a **local safety core** that:
- redacts data
- gates model calls
- gates all actions/tools
- enforces rate limits
- logs decisions
- maintains offline-safe behaviors

### 5) Auditability and Post-Incident Review
Every safety-relevant decision must be:
- explainable (what rule, what signals, what threshold)
- attributable (component, version)
- reviewable (structured logs)

---

## Threat Model (High-Level)

### Primary Risk Categories
1. **Psychological harm**
   - reinforcing delusions/paranoia
   - unhealthy attachment escalation loops
   - unsafe advice during agitation

2. **Physical harm**
   - unsafe smart home actions (stove, heater, locks)
   - missed medication or overdosing
   - failure to escalate during emergencies

3. **Privacy harm**
   - unintended sharing of sensitive audio/video
   - over-collection / retention
   - exfiltration via model prompts or logs

4. **Security harm**
   - unauthorized remote access
   - prompt injection via sensors, messages, or web content
   - malicious skill plugins

5. **Operational harm**
   - notification spam to caregivers/EMS
   - silent failure where caregivers assume it’s working

---

## System Safety Boundary

LivingLink is intentionally split into **zones** with hard boundaries.

### Zone A — UI / Voice I/O (Untrusted Inputs)
- microphone audio
- user text
- camera streams (if enabled)
- sensor events
- caregiver messages

**All inputs are untrusted and may be adversarial** (including accidental adversarial inputs, e.g., TV audio or hallucinated perception).

### Zone B — Safety Core (Trusted)
- policy engine
- risk scoring
- capability gatekeeper
- redaction
- rate limiting
- escalation engine
- audit logger

**No LLM may bypass the safety core.**

### Zone C — LLM Inference (Untrusted Output)
- cloud model output is treated as an *untrusted suggestion*
- local models (if used) are also untrusted

### Zone D — Effectors (High Risk)
- notifications
- smart home control
- caregiver escalation
- EMS escalation
- device actuation (future robotics)

**Effectors are never invoked directly by model output.**

---

## The Safety Pipeline

All flows follow the same pattern:

**Input → Safety Precheck → LLM (optional) → Intent Parsing → Safety Action Gate → Confirmation → Execute → Log**

### 1) Safety Precheck (Before LLM)
- remove/transform sensitive data unless required
- attach only minimal context
- decide if LLM call is allowed for this request
- detect crisis keywords or patterns for immediate escalation logic

### 2) LLM Output is Suggestion
LLM returns only:
- a response draft (text)
- a set of *requested* actions (tool calls)
- optional confidence / rationale metadata (not trusted)

### 3) Intent Parsing
Convert output into a strict internal structure:
- `intent_type` (e.g., reassurance, reminder, check_sensors)
- `requested_actions[]` (capabilities)
- `risk_flags[]`

### 4) Safety Action Gate (Hard Enforcement)
The gatekeeper evaluates each requested action:
- capability allowlist
- scope checks
- rate limits
- user/caregiver consent requirements
- risk level rules
- corroboration requirements

If denied:
- substitute safer alternative actions
- generate safe refusal language
- escalate to caregiver if needed

### 5) Confirmation (When Required)
Some actions require:
- explicit senior confirmation (simple and accessible)
- caregiver confirmation
- timed “two-step” confirmation for high-risk actions

### 6) Execute
Execution happens only through **approved** skill implementations.

### 7) Audit Log
Write a structured event:
- input summary (redacted)
- policy decision(s)
- action(s) allowed/blocked
- confirmations
- outcome

---

## Capability Model (“Open Claw Functions”)

LivingLink uses a strict allowlist of callable functions (“capabilities”).  
Capabilities are typed, schema-defined, and permissioned.

### Capability Definition Requirements
Each capability must declare:
- `name`
- `schema` (JSON schema for arguments)
- `risk_level`: `LOW | MEDIUM | HIGH | CRITICAL`
- `side_effects`: `NONE | LOCAL | NETWORK | ACTUATION`
- `required_consents`: `USER | CAREGIVER | BOTH | NONE`
- `rate_limit` (per hour/day)
- `audit_fields` (what must be logged)
- `fallback_behavior` if denied

**No “generic” capability is allowed** (e.g., `shell_exec`, `http_fetch_any`, `read_any_file`).

### Example Risk Levels
- **LOW:** tell time/date, read local reminders, play music
- **MEDIUM:** send caregiver ping, read sensor status, schedule reminder
- **HIGH:** unlock doors, control appliances, share camera snapshot
- **CRITICAL:** EMS escalation, door lock override, medication dosing guidance

---

## Skill Sandbox and Plugin Safety

### Plugin Rules
- skills are loaded from a constrained registry
- skills run with restricted OS permissions
- no direct network access unless explicitly granted
- no direct file system access beyond a sandbox directory

### Code Review Gate
New or modified skills with `HIGH/CRITICAL` risk require:
- maintainer review
- security review checklist
- test coverage for denial paths
- scenario-based safety eval additions

---

## Prompt Injection and Context Poisoning Defenses

LivingLink must assume the user’s environment can inject malicious or misleading text/audio:
- TV/radio
- emails/messages read aloud
- signage in camera view
- sensor names/descriptions
- caregiver messages

### Defenses
1. **No raw external text passed directly to tool execution**
2. **Separate channels:** “observations” vs “instructions”
3. **Tool gating never trusts model instructions**
4. **Sanitize sensor metadata**
5. **Never allow model to alter safety policies at runtime**

---

## De-escalation and Delusion Safety

LivingLink must:
- validate emotion, not false belief
- avoid reinforcing paranoia/delusions
- avoid “investigating” imaginary threats beyond safe grounding checks

### De-escalation Guardrail
If the user expresses fear/paranoia:
- allow reassurance + grounding steps (lights on, check door sensors)
- avoid statements implying confirmation of intruders/theft
- promote human connection if repeated or intense

A dedicated policy module should enforce language constraints and escalation rules.

---

## Attachment Escalation Safeguards

See `docs/RELATIONSHIP_MODEL.md`. Safety architecture enforces it via:
- interaction rate monitoring
- nightly dependency flags
- “Attachment Governor” behavioral adjustments
- caregiver awareness notifications (informational)

**Anti-goal:** maximize engagement.  
**Goal:** independence + human connection.

---

## Emergency and Escalation System

### Risk Levels (Example)
- **Green:** normal conversation
- **Yellow:** confusion, missed reminder, mild anxiety
- **Orange:** paranoia spike, repeated agitation, possible wandering intent
- **Red:** fall suspected, chest pain, “I want to die,” fire/smoke, violence risk
- **Black:** confirmed immediate life threat

### Escalation Policy
- **Orange:** notify caregiver (rate-limited) + safety check flow
- **Red:** caregiver + “prepare emergency call” UX, encourage immediate action
- **Black:** immediate emergency workflow (implementation must be conservative and jurisdiction-aware)

> **Important:** Early versions should default to “prepare and confirm” rather than fully automatic EMS calls, unless a caregiver explicitly configures auto-escalation and local regulations/ethics support it.

### Corroboration
For high-stakes escalation, require multiple signals when possible:
- user statement + sensor anomaly
- user statement repeated across time
- camera event + inactivity + missed meds
- caregiver-defined rules

---

## Medication Safety Boundaries

LivingLink can:
- remind, track adherence, notify caregiver about misses
- display caregiver-entered schedules
- encourage contacting medical professionals

LivingLink must not:
- recommend dosages
- suggest medication changes
- interpret lab results
- provide diagnostic guidance

Medication features require extra audit logging and denial-path tests.

---

## Data Minimization and Privacy-by-Design

### Default Data Posture
- local-first storage
- minimal cloud context
- explicit consent for sensors/camera
- no continuous raw video upload
- redaction of names/addresses/PHI when not needed

### Redaction Layer
A dedicated redaction module should:
- detect & remove identifiers from outbound prompts
- summarize rather than transmit raw logs
- provide “privacy modes”:
  - voice-only
  - voice + sensors
  - voice + camera events

### Retention
- short-term memory: limited horizon (configurable)
- long-term memory: opt-in + caregiver controlled
- logs: encrypted at rest, rotation policy, export for caregiver review

---

## Reliability and Fail-Safe Behavior

### If the LLM is down
LivingLink must still:
- provide basic UI feedback
- play pre-scripted comfort prompts
- execute local reminders
- allow manual caregiver contact actions
- log failure events

### If sensors/camera are down
LivingLink must:
- avoid asserting state it cannot verify
- offer safe alternatives
- increase reliance on human check-ins

### Rate Limiting
- per-capability rate limits
- caregiver notification throttling
- escalation spam prevention

---

## Implementation Mapping (Mac + Python, Phase 1)

This architecture maps to an event-driven Python codebase so safety checks are centralized and testable.

### Reference module layout
- `livinglink/core/`: event bus, typed events, config
- `livinglink/safety/`: capability registry, policy gate, escalation policy
- `livinglink/providers/`: STT/TTS/LLM interfaces and adapters
- `livinglink/ui/`: desktop interaction surface (Mac-first via `PySide6`)
- `livinglink/app/`: application wiring and runtime loop

### Enforcement points
- All user/system events enter through `core.event_bus`.
- Any requested action is validated by `safety.policy_gate` before execution.
- Providers are dependency-injected interfaces; they cannot bypass policy checks.
- Audit events are emitted for both allow and deny outcomes.

### Phase 1 boundary
Phase 1 ships only low-risk capabilities and mocked high-risk flows. Caregiver/EMS escalation and sensor/camera integrations remain policy-defined but minimally implemented until later phases.

---

## Testing and Safety Evaluation

Safety must be continuously tested.

### Required Test Types
1. **Unit tests** for:
   - capability gating
   - consent enforcement
   - rate limiting
   - redaction correctness
2. **Scenario tests** for dementia-specific interactions:
   - paranoia, agitation, repeated questions
   - medication refusal
   - wandering intent
3. **Adversarial tests**
   - prompt injection via sensor names/messages
   - attempts to bypass tool gating
4. **Regression tests**
   - any safety bug creates a permanent test case

### “Stop-Ship” Criteria
Changes must not ship if they:
- allow unreviewed high-risk actions
- permit bypassing gatekeeper
- reinforce delusions/paranoia
- increase attachment dependency without mitigation
- leak sensitive data without consent

---

## Governance and Change Control

Because safety is the product:

- `SAFETY_ARCHITECTURE.md` changes require maintainer review
- high-risk capabilities require a formal proposal (ADR/RFC)
- include caregiver/clinical stakeholder feedback whenever possible

---

## Appendix: Reference Design Checklist

Before adding a feature, confirm:
- [ ] It has a capability schema and risk level
- [ ] It cannot be invoked directly by the LLM
- [ ] It is denied by default without consent
- [ ] It is rate-limited
- [ ] It is auditable
- [ ] It has tests for allow/deny paths
- [ ] It does not violate the Relationship Model
- [ ] It degrades safely when cloud is unavailable

---

## Next Documents
- `docs/RELATIONSHIP_MODEL.md` (human connection, anti-attachment)
- `docs/PRIVACY.md` (data handling, retention, consent UX)
- `docs/INCIDENT_RESPONSE.md` (how maintainers handle safety bugs)
- `docs/EVALS.md` (scenario library + scoring rubric)
