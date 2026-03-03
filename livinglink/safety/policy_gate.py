from __future__ import annotations

from dataclasses import dataclass

from livinglink.safety.capabilities import CapabilityRegistry, RiskLevel


@dataclass(slots=True)
class PolicyDecision:
    allowed: bool
    reason: str
    reason_code: str


class PolicyGate:
    """Central action gate for capability checks and minimum consent rules."""

    def __init__(self, registry: CapabilityRegistry) -> None:
        self._registry = registry

    def evaluate(
        self,
        capability_name: str,
        granted_consents: set[str] | None = None,
        user_confirmed: bool = False,
    ) -> PolicyDecision:
        capability = self._registry.get(capability_name)
        if not capability:
            return PolicyDecision(False, "Capability is not allowlisted.", "UNKNOWN_CAPABILITY")

        granted = granted_consents or set()
        missing_consents = capability.required_consents - granted
        if missing_consents:
            return PolicyDecision(False, "Required consent missing.", "CONSENT_REQUIRED")

        if capability.risk_level in {RiskLevel.HIGH, RiskLevel.CRITICAL} and not user_confirmed:
            return PolicyDecision(False, "User confirmation required for high-risk action.", "CONFIRM_REQUIRED")

        return PolicyDecision(True, "Action approved.", "ALLOW")
