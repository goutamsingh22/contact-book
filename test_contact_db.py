import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from contact_db import (
    ContactDatabase,
    ContactNotFoundError,
    DuplicateEmailError,
    DuplicatePhoneError,
    ValidationError,
)


class ContactDatabaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temporary_directory = tempfile.TemporaryDirectory()
        self.db_path = Path(self._temporary_directory.name) / "test_contacts.db"
        self.db = ContactDatabase(self.db_path)

    def tearDown(self) -> None:
        self.db.close()
        self._temporary_directory.cleanup()

    def add_contact(self, **overrides: object):
        data = {
            "name": "Ada Lovelace",
            "phone": "+44 (20) 7946-0958",
            "email": "ada@example.com",
            "company": "Analytical Engines",
            "address": "London",
            "birthday": "1815-12-10",
            "notes": "Wrote the first algorithm.",
        }
        data.update(overrides)
        return self.db.create_contact(**data)

    def test_create_and_read_contact(self) -> None:
        contact = self.add_contact(
            name="  Ada   Lovelace ",
            email="ADA@EXAMPLE.COM",
        )

        self.assertEqual(contact.id, 1)
        self.assertEqual(contact.name, "Ada Lovelace")
        self.assertEqual(contact.phone, "+442079460958")
        self.assertEqual(contact.email, "ada@example.com")
        self.assertEqual(contact.company, "Analytical Engines")
        self.assertEqual(contact.address, "London")
        self.assertEqual(contact.birthday, "1815-12-10")
        self.assertEqual(contact.notes, "Wrote the first algorithm.")
        self.assertTrue(contact.created_at)
        self.assertTrue(contact.updated_at)
        self.assertEqual(self.db.get_contact(1), contact)
        self.assertEqual(self.db.find_by_phone("+44 20 7946 0958"), contact)
        self.assertEqual(self.db.find_by_email("Ada@Example.com"), contact)

    def test_optional_fields_default_to_blank(self) -> None:
        contact = self.add_contact(
            phone="5551234567",
            email="",
            company="",
            address="",
            birthday=None,
            notes="",
        )

        self.assertEqual(contact.email, "")
        self.assertEqual(contact.company, "")
        self.assertEqual(contact.address, "")
        self.assertEqual(contact.birthday, "")
        self.assertEqual(contact.notes, "")
        self.assertIsNone(self.db.find_by_email(""))

    def test_duplicate_phone_is_rejected_after_normalization(self) -> None:
        self.add_contact(phone="(555) 123-4567")

        with self.assertRaises(DuplicatePhoneError):
            self.add_contact(
            name="Another Person",
            phone="555.123.4567",
            email="another@example.com",
        )

        self.assertEqual(len(self.db.list_contacts()), 1)

    def test_duplicate_email_is_rejected_case_insensitively(self) -> None:
        self.add_contact()

        with self.assertRaises(DuplicateEmailError):
            self.add_contact(name="Another Person", phone="5551234567", email="ADA@example.com")

        self.assertEqual(len(self.db.list_contacts()), 1)

    def test_blank_emails_can_be_used_by_multiple_contacts(self) -> None:
        self.add_contact(email="")
        self.add_contact(name="Grace Hopper", phone="5551234567", email="")

        self.assertEqual(len(self.db.list_contacts()), 2)

    def test_search_matches_all_text_fields_and_phone(self) -> None:
        self.add_contact()
        self.add_contact(
            name="Grace Hopper",
            phone="5559876543",
            email="grace@navy.example",
            company="US Navy",
            address="Arlington",
            notes="COBOL pioneer",
        )

        self.assertEqual(
            [contact.name for contact in self.db.list_contacts(search="lovelace")],
            ["Ada Lovelace"],
        )
        self.assertEqual(
            [contact.name for contact in self.db.list_contacts(search="navy")],
            ["Grace Hopper"],
        )
        self.assertEqual(
            [contact.name for contact in self.db.list_contacts(search="cobol")],
            ["Grace Hopper"],
        )
        self.assertEqual(
            [contact.name for contact in self.db.list_contacts(search="(555) 987")],
            ["Grace Hopper"],
        )
        self.assertEqual(
            [contact.name for contact in self.db.list_contacts(search="grace@navy")],
            ["Grace Hopper"],
        )

    def test_search_treats_wildcards_as_literal_text(self) -> None:
        self.add_contact(name="100% Real", phone="5551234567", email="real@example.com")
        self.add_contact(
            name="Grace Hopper",
            phone="5559876543",
            email="grace@example.com",
        )

        matches = self.db.list_contacts(search="%")
        self.assertEqual([contact.name for contact in matches], ["100% Real"])
        self.assertEqual(self.db.list_contacts(search="_"), [])

    def test_sort_limit_and_descending(self) -> None:
        self.add_contact(name="Zara Khan", phone="5550000001", email="zara@example.com")
        self.add_contact(name="Amit Patel", phone="5550000002", email="amit@example.com")
        self.add_contact(name="Meera Nair", phone="5550000003", email="meera@example.com")

        self.assertEqual(
            [contact.name for contact in self.db.list_contacts()],
            ["Amit Patel", "Meera Nair", "Zara Khan"],
        )
        self.assertEqual(
            [contact.name for contact in self.db.list_contacts(descending=True)],
            ["Zara Khan", "Meera Nair", "Amit Patel"],
        )
        self.assertEqual(
            [contact.name for contact in self.db.list_contacts(sort="phone", limit=2)],
            ["Zara Khan", "Amit Patel"],
        )

    def test_update_contact(self) -> None:
        contact = self.add_contact()

        updated = self.db.update_contact(
            contact.id,
            name="Ada King",
            email="ada.king@example.com",
            company="",
            notes="Updated notes.",
        )

        self.assertEqual(updated.id, contact.id)
        self.assertEqual(updated.name, "Ada King")
        self.assertEqual(updated.phone, contact.phone)
        self.assertEqual(updated.email, "ada.king@example.com")
        self.assertEqual(updated.company, "")
        self.assertEqual(updated.notes, "Updated notes.")
        self.assertEqual(self.db.get_contact(contact.id), updated)

    def test_update_rejects_duplicate_values(self) -> None:
        first = self.add_contact()
        self.add_contact(
            name="Grace Hopper",
            phone="5559876543",
            email="grace@example.com",
        )

        with self.assertRaises(DuplicatePhoneError):
            self.db.update_contact(first.id, phone="555-987-6543")
        with self.assertRaises(DuplicateEmailError):
            self.db.update_contact(first.id, email="GRACE@example.com")

        self.assertEqual(self.db.get_contact(first.id).phone, first.phone)
        self.assertEqual(self.db.get_contact(first.id).email, first.email)

    def test_update_missing_contact_and_empty_fields(self) -> None:
        with self.assertRaises(ContactNotFoundError):
            self.db.update_contact(999, name="Nobody")
        with self.assertRaises(ValidationError):
            self.db.update_contact(1)
        with self.assertRaises(ValidationError):
            self.db.update_contact(1, unknown="value")

    def test_delete_contact(self) -> None:
        contact = self.add_contact()

        self.assertTrue(self.db.delete_contact(contact.id))
        self.assertIsNone(self.db.get_contact(contact.id))
        self.assertFalse(self.db.delete_contact(contact.id))

    def test_validation_errors(self) -> None:
        future_birthday = (date.today() + timedelta(days=1)).isoformat()
        cases = (
            {"name": "   "},
            {"phone": ""},
            {"phone": "12345"},
            {"phone": "1234567890123456"},
            {"phone": "555-CALL-NOW"},
            {"email": "not-an-email"},
            {"birthday": "10-12-1815"},
            {"birthday": future_birthday},
            {"company": "x" * 101},
            {"address": "x" * 251},
            {"notes": "x" * 1001},
        )
        for overrides in cases:
            with self.subTest(overrides=overrides):
                with self.assertRaises(ValidationError):
                    self.add_contact(**overrides)

        with self.assertRaises(ValidationError):
            self.db.get_contact(0)
        with self.assertRaises(ValidationError):
            self.db.list_contacts(sort="password")
        with self.assertRaises(ValidationError):
            self.db.list_contacts(limit=0)


if __name__ == "__main__":
    unittest.main()
