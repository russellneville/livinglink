# LivingLink Requirements

## Product intent
LivingLink supports seniors in independent living through safe voice interaction, memory aids, de-escalation support, and caregiver coordination.

## Roles
- Senior user: primary in-home user.
- Caregiver: trusted contact receiving non-emergency and emergency updates.
- Maintainer: contributor responsible for code quality and safety controls.

## Functional requirements

### R1: Voice interaction
- The system must support a simple interaction loop: listen, process, respond.
- The interface must expose clear state indicators (`Listening`, `Thinking`, `Speaking`, `Offline`).

Acceptance criteria:
- A user can complete a full talk-response cycle from the desktop app.
- If cloud services are unavailable, the app reports degraded mode without crashing.

### R2: Capability-gated actions
- No model output may execute actions directly.
- All actions must map to an allowlisted capability with schema validation.

Acceptance criteria:
- Requests for unknown capabilities are denied and logged.
- High-risk capabilities require confirmation or escalation policy checks.

### R3: Dementia-aware de-escalation
- The system must validate emotional state while avoiding confirmation of false beliefs.
- Responses must prioritize grounding and safe next steps.

Acceptance criteria:
- Scenario tests flag responses that reinforce paranoia/delusions.
- De-escalation prompts include optional caregiver connection language.

### R4: Short-term memory support
- The system must store short-horizon conversation summaries locally.
- The user can request "what we discussed today".

Acceptance criteria:
- Memory retention window is configurable.
- Memory export requires caregiver or user-approved flow.

### R5: Caregiver notifications
- The system must notify caregiver contacts on configured concern thresholds.
- Notifications must include concise reason codes and time.

Acceptance criteria:
- Repeated triggers are rate-limited.
- Every notification event is auditable.

### R6: Emergency workflow
- Early versions must use a prepare-and-confirm emergency flow by default.
- Auto-escalation must be explicit opt-in with strong warnings.

Acceptance criteria:
- Emergency message drafts include timestamp, context summary, and location metadata if available.
- Emergency actions are blocked if required confirmation is missing.

## Non-functional requirements

### N1: Safety and reliability
- Default behavior must be conservative under uncertainty.
- Critical modules must degrade safely during dependency failure.

### N2: Privacy and data minimization
- Local-first storage is default.
- Cloud transmission requires explicit purpose and minimum necessary data.

### N3: Explainability and auditability
- Safety-relevant decisions must include reason codes.
- Logs must support post-incident reconstruction.

### N4: Accessibility
- Desktop UI must support large controls, high contrast modes, and minimal cognitive load.

## Out of scope (MVP)
- Medical diagnosis or dosage guidance
- Open-ended internet browsing by default
- Fully autonomous emergency calling without opt-in policy
- Unrestricted device actuation

## Traceability
- Safety architecture: `docs/SAFETY_ARCHITECTURE.md`
- Privacy requirements: `docs/PRIVACY.md`
- Incident handling: `docs/INCIDENT_RESPONSE.md`
