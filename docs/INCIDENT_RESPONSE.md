# LivingLink Incident Response

## Purpose
This runbook defines how maintainers respond to safety, security, and privacy incidents in LivingLink.

## Incident categories
- Safety incident: behavior that can cause psychological or physical harm.
- Privacy incident: unauthorized exposure, retention, or transmission of sensitive data.
- Security incident: unauthorized access, code execution, or supply-chain compromise.
- Reliability incident: failure mode that blocks critical safety workflows.

## Severity levels
- `SEV-1 Critical`: immediate risk of severe harm or active compromise.
- `SEV-2 High`: serious safety/privacy/security issue with plausible near-term harm.
- `SEV-3 Medium`: contained issue with mitigations available.
- `SEV-4 Low`: minor issue with limited impact.

## Response targets
- SEV-1: acknowledge within 1 hour, begin containment immediately.
- SEV-2: acknowledge within 4 hours, mitigation plan same day.
- SEV-3: acknowledge within 1 business day.
- SEV-4: acknowledge within 3 business days.

## Response workflow

### 1) Triage
- Collect report details, affected versions, and reproducibility.
- Classify severity and incident category.
- Assign incident commander (single accountable lead).

### 2) Containment
- Disable or gate impacted capabilities.
- Ship configuration kill-switch updates where possible.
- Revoke compromised tokens/keys and rotate credentials.

### 3) Assessment
- Determine user/caregiver impact scope.
- Verify whether logs contain enough evidence for root cause.
- Identify temporary safeguards required before full fix.

### 4) Eradication and recovery
- Implement patch and tests that reproduce and prevent recurrence.
- Validate in staging with safety scenarios.
- Release fix with explicit version notes.

### 5) Communication
- Notify affected users/caregivers when risk is material.
- Publish maintainer advisory for severe incidents.
- Provide mitigation steps and upgrade guidance.

### 6) Post-incident review
- Complete postmortem within 7 days for SEV-1/2.
- Document root cause, contributing factors, and corrective actions.
- Add regression tests and policy updates.

## Emergency safety override
The project must support fast disablement of high-risk capabilities via configuration. Emergency override changes require:
- incident ticket reference
- maintainer approval trail
- documented rollback criteria

## Evidence handling
- Preserve relevant logs with redaction where required.
- Restrict incident data access to response team.
- Track chain of custody for sensitive artifacts.

## Required artifacts per incident
- Timeline of events (UTC)
- Impact statement
- Technical root cause
- Remediation and prevention actions
- Test additions and policy/documentation changes

## Reporting channels
- Security and privacy reports: designated maintainer contact in repository security policy
- Safety behavior reports: issue template with structured scenario fields

## Related docs
- `docs/SAFETY_ARCHITECTURE.md`
- `docs/PRIVACY.md`
- `docs/REQUIREMENTS.md`
