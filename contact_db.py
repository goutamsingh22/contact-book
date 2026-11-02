"""SQLite data layer for the Contact Book application."""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS contacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL CHECK (length(trim(name)) > 0),
    phone TEXT NOT NULL UNIQUE CHECK (length(phone) > 0),
    email TEXT NOT NULL DEFAULT '',
    company TEXT NOT NULL DEFAULT '',
    address TEXT NOT NULL DEFAULT '',
    birthday TEXT NOT NULL DEFAULT '',
    notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_contacts_name ON contacts (name COLLATE NOCASE);
CREATE INDEX IF NOT EXISTS idx_contacts_phone ON contacts (phone);

CREATE UNIQUE INDEX IF NOT EXISTS idx_contacts_email_unique
    ON contacts (email COLLATE NOCASE) WHERE email <> '';
"""

SORT_COLUMNS = {
    "id": "id",
    "name": "name COLLATE NOCASE",
    "phone": "phone",
    "email": "email COLLATE NOCASE",
    "company": "company COLLATE NOCASE",
    "created_at": "created_at",
    "updated_at": "updated_at",
}

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_PATTERN = re.compile(r"^\+?[\d\s().-]+$")


class ContactError(Exception):
    """Base class for contact database errors."""


class ValidationError(ContactError):
    """Raised when contact data is invalid."""


class DuplicatePhoneError(ContactError):
    """Raised when a phone number is already saved."""


class DuplicateEmailError(ContactError):
    """Raised when an email address is already saved."""


class ContactNotFoundError(ContactError):
    """Raised when a requested contact does not exist."""


@dataclass(frozen=True, slots=True)
class Contact:
    id: int
    name: str
    phone: str
    email: str
    company: str
    address: str
    birthday: str
    notes: str
    created_at: str
    updated_at: str

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "Contact":
        return cls(
            id=row["id"],
            name=row["name"],
            phone=row["phone"],
            email=row["email"],
            company=row["company"],
            address=row["address"],
            birthday=row["birthday"],
            notes=row["notes"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


def _clean_required_text(value: Any, field: str, max_length: int) -> str:
    if not isinstance(value, str):
        raise ValidationError(f"{field} must be text.")
    cleaned = " ".join(value.split())
    if not cleaned:
        raise ValidationError(f"{field} cannot be empty.")
    if len(cleaned) > max_length:
        raise ValidationError(f"{field} must be at most {max_length} characters.")
    return cleaned


def _clean_optional_text(
    value: Any,
    field: str,
    max_length: int,
    *,
    keep_lines: bool = False,
) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ValidationError(f"{field} must be text.")
    cleaned = value.strip("\r\n ") if keep_lines else " ".join(value.split())
    if len(cleaned) > max_length:
        raise ValidationError(f"{field} must be at most {max_length} characters.")
    return cleaned


def _clean_phone(value: Any) -> str:
    if not isinstance(value, str):
        raise ValidationError("phone must be text.")
    phone = value.strip()
    if not phone:
        raise ValidationError("phone cannot be empty.")
    if not PHONE_PATTERN.match(phone):
        raise ValidationError(
            "phone can contain digits, spaces, parentheses, dots, hyphens, "
            "and an optional leading +."
        )

    digits = re.sub(r"\D", "", phone)
    if not 7 <= len(digits) <= 15:
        raise ValidationError("phone must contain between 7 and 15 digits.")
    return f"+{digits}" if phone.startswith("+") else digits


def _clean_email(value: Any) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ValidationError("email must be text.")
    email = value.strip().lower()
    if not email:
        return ""
    if len(email) > 254 or not EMAIL_PATTERN.match(email):
        raise ValidationError("email must be a valid address, such as name@example.com.")
    return email


def _clean_birthday(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, date):
        parsed = value
    else:
        text = str(value).strip()
        if not text:
            return ""
        try:
            parsed = date.fromisoformat(text)
        except ValueError:
            raise ValidationError("birthday must use YYYY-MM-DD format.") from None

    if parsed > date.today():
        raise ValidationError("birthday cannot be in the future.")
    return parsed.isoformat()


def _clean_id(contact_id: Any) -> int:
    if isinstance(contact_id, bool):
        raise ValidationError("contact ID must be a positive whole number.")
    try:
        clean_id = int(contact_id)
    except (TypeError, ValueError):
        raise ValidationError("contact ID must be a positive whole number.") from None
    if clean_id < 1:
        raise ValidationError("contact ID must be a positive whole number.")
    return clean_id


def _like_term(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def _duplicate_error(exc: sqlite3.IntegrityError) -> ContactError:
    message = str(exc).upper()
    if "PHONE" in message:
        return DuplicatePhoneError("A contact with that phone number already exists.")
    if "EMAIL" in message:
        return DuplicateEmailError("A contact with that email address already exists.")
    return ContactError("The contact could not be saved because it conflicts with another record.")


class ContactDatabase:
    """A small, parameterized SQL wrapper around a SQLite contacts table."""

    def __init__(self, db_path: str | Path = "contacts.db") -> None:
        self.db_path = str(db_path)
        self._connection = sqlite3.connect(self.db_path)
        self._connection.row_factory = sqlite3.Row
        self._create_schema()

    def _create_schema(self) -> None:
        with self._connection:
            self._connection.executescript(SCHEMA)

    def close(self) -> None:
        self._connection.close()

    def __enter__(self) -> "ContactDatabase":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()

    def create_contact(
        self,
        name: str,
        phone: str,
        email: str = "",
        company: str = "",
        address: str = "",
        birthday: str | date | None = None,
        notes: str = "",
    ) -> Contact:
        clean_name = _clean_required_text(name, "name", 100)
        clean_phone = _clean_phone(phone)
        clean_email = _clean_email(email)
        clean_company = _clean_optional_text(company, "company", 100)
        clean_address = _clean_optional_text(address, "address", 250)
        clean_birthday = _clean_birthday(birthday)
        clean_notes = _clean_optional_text(notes, "notes", 1000, keep_lines=True)

        try:
            with self._connection:
                cursor = self._connection.execute(
                    """
                    INSERT INTO contacts
                        (name, phone, email, company, address, birthday, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        clean_name,
                        clean_phone,
                        clean_email,
                        clean_company,
                        clean_address,
                        clean_birthday,
                        clean_notes,
                    ),
                )
        except sqlite3.IntegrityError as exc:
            raise _duplicate_error(exc) from None

        contact = self.get_contact(cursor.lastrowid)
        if contact is None:
            raise ContactError("The contact could not be loaded after insertion.")
        return contact

    def get_contact(self, contact_id: int) -> Contact | None:
        row = self._connection.execute(
            "SELECT * FROM contacts WHERE id = ?",
            (_clean_id(contact_id),),
        ).fetchone()
        return Contact.from_row(row) if row else None

    def find_by_phone(self, phone: str) -> Contact | None:
        row = self._connection.execute(
            "SELECT * FROM contacts WHERE phone = ?",
            (_clean_phone(phone),),
        ).fetchone()
        return Contact.from_row(row) if row else None

    def find_by_email(self, email: str) -> Contact | None:
        clean_email = _clean_email(email)
        if not clean_email:
            return None
        row = self._connection.execute(
            "SELECT * FROM contacts WHERE email = ? COLLATE NOCASE",
            (clean_email,),
        ).fetchone()
        return Contact.from_row(row) if row else None

    def list_contacts(
        self,
        search: str | None = None,
        sort: str = "name",
        descending: bool = False,
        limit: int | None = None,
    ) -> list[Contact]:
        if sort not in SORT_COLUMNS:
            valid = ", ".join(SORT_COLUMNS)
            raise ValidationError(f"sort must be one of: {valid}.")
        if limit is not None and limit < 1:
            raise ValidationError("limit must be a positive number.")

        clauses: list[str] = []
        parameters: list[Any] = []

        if search and search.strip():
            term = _like_term(search.strip())
            clauses.extend(
                (
                    "name COLLATE NOCASE LIKE ? ESCAPE '\\'",
                    "email COLLATE NOCASE LIKE ? ESCAPE '\\'",
                    "company COLLATE NOCASE LIKE ? ESCAPE '\\'",
                    "address COLLATE NOCASE LIKE ? ESCAPE '\\'",
                    "notes COLLATE NOCASE LIKE ? ESCAPE '\\'",
                )
            )
            parameters.extend((term, term, term, term, term))

            phone_digits = re.sub(r"\D", "", search)
            if phone_digits:
                clauses.append("phone LIKE ? ESCAPE '\\'")
                parameters.append(f"%{phone_digits}%")

        query = "SELECT * FROM contacts"
        if clauses:
            query += " WHERE (" + " OR ".join(clauses) + ")"
        query += f" ORDER BY {SORT_COLUMNS[sort]}"
        query += " DESC" if descending else " ASC"
        query += ", id ASC"

        if limit is not None:
            query += " LIMIT ?"
            parameters.append(int(limit))

        rows = self._connection.execute(query, parameters).fetchall()
        return [Contact.from_row(row) for row in rows]

    def update_contact(self, contact_id: int, **fields: Any) -> Contact:
        clean_id = _clean_id(contact_id)
        if not fields:
            raise ValidationError("Provide at least one field to update.")

        allowed = {"name", "phone", "email", "company", "address", "birthday", "notes"}
        unknown = set(fields) - allowed
        if unknown:
            names = ", ".join(sorted(unknown))
            raise ValidationError(f"Unknown field(s): {names}.")
        if self.get_contact(clean_id) is None:
            raise ContactNotFoundError(f"No contact found with ID {clean_id}.")

        updates: dict[str, Any] = {}
        if "name" in fields:
            updates["name"] = _clean_required_text(fields["name"], "name", 100)
        if "phone" in fields:
            updates["phone"] = _clean_phone(fields["phone"])
        if "email" in fields:
            updates["email"] = _clean_email(fields["email"])
        if "company" in fields:
            updates["company"] = _clean_optional_text(fields["company"], "company", 100)
        if "address" in fields:
            updates["address"] = _clean_optional_text(fields["address"], "address", 250)
        if "birthday" in fields:
            updates["birthday"] = _clean_birthday(fields["birthday"])
        if "notes" in fields:
            updates["notes"] = _clean_optional_text(
                fields["notes"], "notes", 1000, keep_lines=True
            )

        assignments = ", ".join(f"{column} = ?" for column in updates)
        parameters = list(updates.values())
        parameters.append(clean_id)

        try:
            with self._connection:
                self._connection.execute(
                    f"UPDATE contacts SET {assignments}, updated_at = datetime('now') "
                    "WHERE id = ?",
                    parameters,
                )
        except sqlite3.IntegrityError as exc:
            raise _duplicate_error(exc) from None

        contact = self.get_contact(clean_id)
        if contact is None:
            raise ContactNotFoundError(f"No contact found with ID {clean_id}.")
        return contact

    def delete_contact(self, contact_id: int) -> bool:
        with self._connection:
            cursor = self._connection.execute(
                "DELETE FROM contacts WHERE id = ?",
                (_clean_id(contact_id),),
            )
        return cursor.rowcount > 0
