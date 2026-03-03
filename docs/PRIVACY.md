# LivingLink Privacy Model

## Principles
- Local-first by default
- Explicit consent for sensitive sensors and sharing
- Data minimization at collection, transmission, and retention
- Caregiver transparency with user dignity preserved

## Data categories

### Core interaction data
- Voice transcripts
- Assistant responses
- Session summaries

Default posture:
- Stored locally in encrypted form.
- Not shared externally unless required for configured provider calls.

### Household signal data
- Sensor events (motion, door, appliance state)
- Camera-derived events (state transitions, not continuous footage)

Default posture:
- Disabled by default.
- Requires explicit per-source opt-in.

### Care coordination data
- Caregiver contacts
- Notification history
- Escalation event metadata

Default posture:
- Stored locally.
- Shared only with configured contacts and channels.

## Consent model

### Consent levels
- `none`: feature disabled
- `local_only`: process and store only on device
- `cloud_processing`: allowed to send minimal context to configured service
- `caregiver_share`: allowed to share specific event summaries with caregivers

### Consent rules
- Consent must be per-feature and revocable.
- Revocation must stop future collection immediately.
- High-risk capabilities require explicit re-confirmation after major updates.

## Data flow controls

### Collection controls
- Record only data required for current function.
- Avoid continuous background capture unless explicitly enabled.

### Redaction controls
Before external calls:
- remove direct identifiers when not required
- summarize instead of sending raw historical logs
- attach minimum context needed for response quality

### Egress controls
- All external calls pass through policy gate checks.
- Capability metadata identifies side effects and network behavior.

## Retention and deletion

### Default retention windows
- Raw transcripts: short window (for example, 7-30 days, configurable)
- Session summaries: medium window (for example, 30-90 days, configurable)
- Audit logs: longer retention for safety review (for example, 90-365 days, configurable)

### Deletion requirements
- User/caregiver can delete local history from settings.
- Deletion requests must remove associated indexes and derived summaries when feasible.
- Incident-critical logs may be retained per configured policy and legal obligations.

## Security controls
- Encryption at rest for sensitive local stores
- Encrypted transport for network operations
- Principle of least privilege for skills and plugins
- Signed release artifacts and dependency review for supply-chain risk

## Transparency requirements
- User-visible notice when microphone, camera, or sensor features are active
- Clear disclosure of what data leaves device and why
- Caregiver-readable logs for escalations and high-risk actions

## Prohibited behaviors
- Selling user data
- Using household data for ad targeting
- Silent activation of new high-risk collection features
- Sending raw video/audio continuously by default

## Related docs
- `docs/SAFETY_ARCHITECTURE.md`
- `docs/RELATIONSHIP_MODEL.md`
- `docs/INCIDENT_RESPONSE.md`
