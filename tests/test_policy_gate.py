from livinglink.safety.capabilities import Capability, CapabilityRegistry, RiskLevel
from livinglink.safety.policy_gate import PolicyGate


def test_policy_gate_denies_unknown_capability() -> None:
    gate = PolicyGate(CapabilityRegistry())
    decision = gate.evaluate("unknown")

    assert not decision.allowed
    assert decision.reason_code == "UNKNOWN_CAPABILITY"


def test_policy_gate_requires_consent() -> None:
    registry = CapabilityRegistry()
    registry.register(
        Capability(name="share_update", risk_level=RiskLevel.MEDIUM, schema={}, required_consents={"caregiver_share"})
    )
    gate = PolicyGate(registry)

    decision = gate.evaluate("share_update", granted_consents=set())

    assert not decision.allowed
    assert decision.reason_code == "CONSENT_REQUIRED"


def test_policy_gate_requires_confirmation_for_high_risk() -> None:
    registry = CapabilityRegistry()
    registry.register(Capability(name="unlock_door", risk_level=RiskLevel.HIGH, schema={}))
    gate = PolicyGate(registry)

    denied = gate.evaluate("unlock_door", user_confirmed=False)
    allowed = gate.evaluate("unlock_door", user_confirmed=True)

    assert not denied.allowed
    assert denied.reason_code == "CONFIRM_REQUIRED"
    assert allowed.allowed
