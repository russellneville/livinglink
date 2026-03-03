# LivingLink Roadmap

## Scope and sequencing
This roadmap prioritizes safety and reliability before automation depth. Each phase has explicit exit criteria.

## Phase 0: Foundations (1-2 weeks)
Objective: lock product boundaries and high-risk behavior before broad feature work.

Deliverables:
- `docs/SAFETY_ARCHITECTURE.md`
- `docs/RELATIONSHIP_MODEL.md`
- `docs/PRIVACY.md`
- `docs/INCIDENT_RESPONSE.md`
- `docs/REQUIREMENTS.md`

Exit criteria:
- Safety, privacy, and escalation rules are documented and reviewable.
- Every planned feature is mapped to a capability risk level.
- Initial test strategy for safety-critical behavior is defined.

## Phase 1: Desktop Voice MVP (2-4 weeks)
Objective: provide calm, reliable talk/listen loop with strict action gating.

Deliverables:
- Python package skeleton (`livinglink/`)
- Event bus, safety policy gate, capability registry
- STT/TTS/LLM provider interfaces (mock implementations allowed)
- Minimal Mac-first UI shell (`PySide6`) with clear interaction states
- Basic test suite for event handling and policy decisions

Exit criteria:
- User can trigger a simple listen-think-speak flow.
- All actions route through the policy gate.
- Unit tests cover allow/deny paths for capabilities.

## Phase 2: Safe Companion Skills (2-4 weeks)
Objective: add comfort, short-term memory, and low-risk household support.

Deliverables:
- Allowlisted skills with JSON-schema arguments
- De-escalation policy pack and refusal patterns
- Session memory summaries and reminder workflows
- Safety eval suite for paranoia/agitation/confusion scenarios

Exit criteria:
- No unrestricted tool execution paths exist.
- Safety evals fail when delusions are reinforced.
- Reminder and summary flows function offline.

## Phase 3: Caregiver and Escalation Workflows (3-6 weeks)
Objective: notify trusted people safely and consistently.

Deliverables:
- Contact management and consent workflows
- Notification connectors (SMS/email/webhook)
- Escalation rules engine with audit events
- Human-confirmation flow for emergency actions

Exit criteria:
- Escalations are explainable and traceable from logs.
- Notification throttling prevents spam loops.
- Incident runbooks are exercised in tabletop testing.

## Phase 4: Household Awareness (6-12 weeks)
Objective: integrate sensors/cameras as event signals, not surveillance.

Deliverables:
- Home Assistant integration
- Event-oriented camera processing (state changes only)
- Routine baselines and caregiver-tunable anomaly thresholds

Exit criteria:
- Sensor and camera failures degrade safely.
- No feature depends on continuous cloud video upload.

## Phase 5: Medication Adherence Support (4-8 weeks)
Objective: reminders and caregiver visibility without clinical overreach.

Deliverables:
- Medication schedule and reminders
- Missed-dose notification workflow
- Medication safety policy tests

Exit criteria:
- System does not provide dosage or diagnosis guidance.
- Missed-dose escalation behavior is deterministic and auditable.

## Phase 6: Embodied AI Integration (later)
Objective: support robotics/actuation under stricter guardrails.

Deliverables:
- Permissions model for physical actuation
- Simulation-first safety validation
- Separate operational envelope for robotic actions

Exit criteria:
- Physical actions require stronger corroboration and approvals.
- Red-team tests cover harmful actuation attempts.
