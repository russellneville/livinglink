from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class RuntimeConfig:
    app_name: str = "LivingLink"
    offline_mode: bool = True
    require_user_confirmation_for_high_risk: bool = True
    confirmation_ttl_seconds: int = 300
    notification_throttle_seconds: int = 300
    auto_ems_enabled: bool = False
    emergency_pending_ttl_seconds: int = 300
