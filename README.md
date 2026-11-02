# Contact Book
A clean, dependency-free desktop contact manager built with Python, Tkinter,
and SQLite. Add, search, update, and delete contacts while keeping everything
stored safely in a local database.

## Features
- Desktop interface with a searchable contact list and detail form
- Add, view, update, and delete contacts
- Search across name, phone, email, company, address, and notes
- Phone numbers are validated and normalized before they are saved
- Duplicate phone numbers and email addresses are rejected
- Optional company, address, birthday, and notes fields
- SQLite database created automatically on first launch
- Parameterized SQL queries and an allowlist for sort columns
- Unit tests for the data layer using Python's built-in `unittest`

## Requirements
- Python 3.10 or newer
- Tkinter, which is included with the standard Windows and macOS Python
  installers. On Linux, install the `python3-tk` package if needed.

No third-party Python packages are required.

## Quick start

Run the application from this directory:

```powershell
python main.py
```

The first launch creates `contacts.db` beside `main.py`.

To use a different database file:

```powershell
python main.py --db C:\Users\you\Documents\my-contacts.db
```

## Using the app

1. Select **New Contact** to clear the form.
2. Fill in a name and phone number. Everything else is optional.
3. Select **Save Contact**.
4. Select a contact in the list to edit it, then select **Save Contact** again.
5. Use the search box to filter the list as you type.
6. Select a contact and choose **Delete** to remove it. You will be asked to
   confirm.

Birthdays use the `YYYY-MM-DD` format. Phone numbers may include spaces,
parentheses, dots, and hyphens, with an optional leading `+`. They are stored
in a normalized form so searches work with or without punctuation.

### Keyboard shortcuts

| Shortcut | Action |
| --- | --- |
| `Ctrl+N` | Start a new contact |
| `Ctrl+S` | Save the current contact |
| `Ctrl+F` | Focus the search box |
| `Esc` | Clear the search |
| `F5` | Refresh the contact list |
| `Delete` | Delete the selected contact (with confirmation) |

## Project structure

```text
contact-book/
|-- main.py            # Tkinter desktop interface
|-- contact_db.py      # Validation, schema, and SQLite operations
|-- test_contact_db.py # Unit tests for the data layer
|-- README.md
`-- contacts.db        # Created at runtime, ignored by Git
```

## Database schema
The data layer creates this table and its indexes automatically:

```sql
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
```

The partial unique index permits any number of contacts without an email
address while still preventing duplicate, case-insensitive email addresses.
Phone numbers are normalized to digits (with an optional leading `+`) before
being stored.

## Data layer

`contact_db.py` can also be used without the desktop interface:

```python
from contact_db import ContactDatabase

with ContactDatabase("contacts.db") as db:
    contact = db.create_contact(
        name="Ada Lovelace",
        phone="+44 20 7946 0958",
        email="ada@example.com",
        company="Analytical Engines",
        birthday="1815-12-10",
    )

    matches = db.list_contacts(search="ada")
    db.update_contact(contact.id, company="Independent")
    db.delete_contact(contact.id)
```

Invalid input raises `ValidationError`. Unique conflicts raise
`DuplicatePhoneError` or `DuplicateEmailError`, and missing records raise
`ContactNotFoundError`. All of these inherit from `ContactError`.

## Running tests

```powershell
python -m unittest discover -v
```



The tests use temporary database files, so your `contacts.db` is never modified.
