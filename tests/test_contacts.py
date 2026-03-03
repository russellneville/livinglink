from __future__ import annotations

from livinglink.care.contacts import CaregiverContact, ContactBook


def test_contact_book_primary_returns_consented_primary() -> None:
    book = ContactBook()
    book.add(CaregiverContact(contact_id="c1", name="A", consented=True, is_primary=True))
    book.add(CaregiverContact(contact_id="c2", name="B", consented=True, is_primary=False))

    primary = book.primary()

    assert primary is not None
    assert primary.contact_id == "c1"


def test_contact_book_primary_ignores_unconsented_primary() -> None:
    book = ContactBook()
    book.add(CaregiverContact(contact_id="c1", name="A", consented=False, is_primary=True))

    assert book.primary() is None


def test_contact_book_list_consented_filters_correctly() -> None:
    book = ContactBook()
    book.add(CaregiverContact(contact_id="c1", name="A", consented=True))
    book.add(CaregiverContact(contact_id="c2", name="B", consented=False))

    consented_ids = {contact.contact_id for contact in book.list_consented()}

    assert consented_ids == {"c1"}
