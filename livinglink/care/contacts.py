from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class CaregiverContact:
    contact_id: str
    name: str
    channels: tuple[str, ...] = ("email",)
    consented: bool = True
    is_primary: bool = False


@dataclass(slots=True)
class ContactBook:
    _contacts: dict[str, CaregiverContact] = field(default_factory=dict)

    def add(self, contact: CaregiverContact) -> None:
        self._contacts[contact.contact_id] = contact

    def get(self, contact_id: str) -> CaregiverContact | None:
        return self._contacts.get(contact_id)

    def list_consented(self) -> list[CaregiverContact]:
        return [c for c in self._contacts.values() if c.consented]

    def primary(self) -> CaregiverContact | None:
        for contact in self._contacts.values():
            if contact.is_primary and contact.consented:
                return contact
        return None
