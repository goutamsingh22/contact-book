"""Desktop Contact Book built with Tkinter and SQLite."""

from __future__ import annotations

import argparse
import sqlite3
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Sequence

from contact_db import Contact, ContactDatabase, ContactError

FONT = "Segoe UI"
BG = "#eef2f7"
CARD = "#ffffff"
TEXT = "#172033"
MUTED = "#64748b"
ACCENT = "#2563eb"
ACCENT_HOVER = "#1d4ed8"
ACCENT_PRESSED = "#1e40af"
BORDER = "#dbe3ee"
DANGER = "#b91c1c"
DEFAULT_DB_PATH = Path(__file__).with_name("contacts.db")


class ContactBookApp:
    def __init__(self, root: tk.Tk, database: ContactDatabase) -> None:
        self.root = root
        self.db = database
        self.current_id: int | None = None
        self._search_job: str | None = None

        self.search_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Ready")
        self.form_title_var = tk.StringVar(value="New contact")
        self.name_var = tk.StringVar()
        self.phone_var = tk.StringVar()
        self.email_var = tk.StringVar()
        self.company_var = tk.StringVar()
        self.birthday_var = tk.StringVar()

        self._configure_window()
        self._configure_styles()
        self._build_layout()
        self._bind_events()
        self.refresh()

    def _configure_window(self) -> None:
        self.root.title("Contact Book")
        self.root.configure(background=BG)
        width, height = 1120, 720
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = max((screen_width - width) // 2, 0)
        y = max((screen_height - height) // 2, 0)
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        self.root.minsize(920, 620)

    def _configure_styles(self) -> None:
        style = ttk.Style(self.root)
        if "clam" in style.theme_names():
            style.theme_use("clam")

        style.configure("App.TFrame", background=BG)
        style.configure("Card.TFrame", background=CARD)
        style.configure("Status.TFrame", background=BG)
        style.configure(
            "Title.TLabel",
            background=BG,
            foreground=TEXT,
            font=(FONT, 22, "bold"),
        )
        style.configure(
            "Subtitle.TLabel",
            background=BG,
            foreground=MUTED,
            font=(FONT, 10),
        )
        style.configure(
            "CardTitle.TLabel",
            background=CARD,
            foreground=TEXT,
            font=(FONT, 13, "bold"),
        )
        style.configure(
            "FormLabel.TLabel",
            background=CARD,
            foreground=MUTED,
            font=(FONT, 9, "bold"),
        )
        style.configure(
            "Hint.TLabel",
            background=CARD,
            foreground=MUTED,
            font=(FONT, 9),
        )
        style.configure(
            "Status.TLabel",
            background=BG,
            foreground=MUTED,
            font=(FONT, 9),
        )
        style.configure(
            "TEntry",
            padding=(8, 7),
            fieldbackground=CARD,
            bordercolor=BORDER,
            lightcolor=BORDER,
            darkcolor=BORDER,
        )
        style.map("TEntry", bordercolor=[("focus", ACCENT)])

        style.configure(
            "Accent.TButton",
            background=ACCENT,
            foreground="white",
            font=(FONT, 10, "bold"),
            padding=(16, 9),
            borderwidth=0,
            focusthickness=0,
        )
        style.map(
            "Accent.TButton",
            background=[
                ("pressed", ACCENT_PRESSED),
                ("active", ACCENT_HOVER),
                ("disabled", "#93c5fd"),
            ],
            foreground=[("disabled", "#eff6ff")],
        )
        style.configure(
            "Secondary.TButton",
            background="#edf2f9",
            foreground=TEXT,
            font=(FONT, 10),
            padding=(14, 9),
            borderwidth=0,
        )
        style.map(
            "Secondary.TButton",
            background=[("pressed", "#dbe3ee"), ("active", "#e2e8f0")],
        )
        style.configure(
            "Danger.TButton",
            background="#fee2e2",
            foreground=DANGER,
            font=(FONT, 10, "bold"),
            padding=(14, 9),
            borderwidth=0,
        )
        style.map(
            "Danger.TButton",
            background=[("pressed", "#fecaca"), ("active", "#fecaca")],
            foreground=[("disabled", "#fca5a5")],
        )
        style.configure(
            "Treeview",
            background=CARD,
            fieldbackground=CARD,
            foreground=TEXT,
            rowheight=34,
            borderwidth=0,
            font=(FONT, 10),
        )
        style.configure(
            "Treeview.Heading",
            background="#f1f5f9",
            foreground=MUTED,
            font=(FONT, 9, "bold"),
            relief="flat",
            padding=(8, 8),
        )
        style.map("Treeview.Heading", background=[("active", "#e2e8f0")])
        style.map(
            "Treeview",
            background=[("selected", "#dbeafe")],
            foreground=[("selected", TEXT)],
        )

    def _build_layout(self) -> None:
        self.root.rowconfigure(1, weight=1)
        self.root.columnconfigure(0, weight=1)

        header = ttk.Frame(self.root, style="App.TFrame", padding=(24, 20, 24, 10))
        header.grid(row=0, column=0, sticky="ew")
        ttk.Label(header, text="Contact Book", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            header,
            text="Keep your people, numbers, and details in one place.",
            style="Subtitle.TLabel",
        ).pack(anchor="w", pady=(2, 0))

        body = ttk.Frame(self.root, style="App.TFrame", padding=(24, 8, 24, 8))
        body.grid(row=1, column=0, sticky="nsew")
        body.columnconfigure(0, weight=3, minsize=540)
        body.columnconfigure(1, weight=2, minsize=340)
        body.rowconfigure(0, weight=1)

        left = ttk.Frame(body, style="Card.TFrame", padding=18)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        right = ttk.Frame(body, style="Card.TFrame", padding=20)
        right.grid(row=0, column=1, sticky="nsew")

        self._build_contact_list(left)
        self._build_contact_form(right)

        status = ttk.Frame(self.root, style="Status.TFrame", padding=(26, 6, 26, 12))
        status.grid(row=2, column=0, sticky="ew")
        ttk.Label(status, textvariable=self.status_var, style="Status.TLabel").pack(
            anchor="w"
        )

    def _build_contact_list(self, parent: ttk.Frame) -> None:
        parent.rowconfigure(3, weight=1)
        parent.columnconfigure(0, weight=1)

        title_row = ttk.Frame(parent, style="Card.TFrame")
        title_row.grid(row=0, column=0, sticky="ew")
        title_row.columnconfigure(0, weight=1)
        ttk.Label(title_row, text="All contacts", style="CardTitle.TLabel").grid(
            row=0, column=0, sticky="w"
        )

        ttk.Label(parent, text="SEARCH", style="FormLabel.TLabel").grid(
            row=1, column=0, sticky="w", pady=(16, 4)
        )
        search_row = ttk.Frame(parent, style="Card.TFrame")
        search_row.grid(row=2, column=0, sticky="ew")
        search_row.columnconfigure(0, weight=1)
        self.search_entry = ttk.Entry(search_row, textvariable=self.search_var)
        self.search_entry.grid(row=0, column=0, sticky="ew")
        ttk.Button(
            search_row,
            text="Clear",
            style="Secondary.TButton",
            command=self.clear_search,
        ).grid(row=0, column=1, padx=(8, 0))

        tree_frame = ttk.Frame(parent, style="Card.TFrame")
        tree_frame.grid(row=3, column=0, sticky="nsew", pady=(12, 12))
        tree_frame.rowconfigure(0, weight=1)
        tree_frame.columnconfigure(0, weight=1)

        columns = ("name", "phone", "email", "company")
        self.tree = ttk.Treeview(
            tree_frame,
            columns=columns,
            show="headings",
            selectmode="browse",
        )
        headings = {
            "name": ("Name", 175, 120),
            "phone": ("Phone", 125, 100),
            "email": ("Email", 190, 130),
            "company": ("Company", 120, 90),
        }
        for column, (label, width, minwidth) in headings.items():
            self.tree.heading(column, text=label, anchor="w")
            self.tree.column(column, width=width, minwidth=minwidth, anchor="w")
        self.tree.tag_configure("odd", background="#f8fafc")
        self.tree.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scrollbar.set)

        actions = ttk.Frame(parent, style="Card.TFrame")
        actions.grid(row=4, column=0, sticky="ew")
        actions.columnconfigure(1, weight=1)
        ttk.Button(
            actions,
            text="New Contact",
            style="Accent.TButton",
            command=self.new_contact,
        ).grid(row=0, column=0, sticky="w")
        self.delete_button = ttk.Button(
            actions,
            text="Delete",
            style="Danger.TButton",
            command=self.delete_contact,
        )
        self.delete_button.grid(row=0, column=2, sticky="e")
        self.delete_button.state(["disabled"])

    def _build_contact_form(self, parent: ttk.Frame) -> None:
        parent.columnconfigure(0, minsize=82)
        parent.columnconfigure(1, weight=1)
        parent.rowconfigure(8, weight=1)

        ttk.Label(
            parent, textvariable=self.form_title_var, style="CardTitle.TLabel"
        ).grid(row=0, column=0, columnspan=2, sticky="w")
        ttk.Label(
            parent, text="* required", style="Hint.TLabel"
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(2, 14))

        self.name_entry = self._add_entry(parent, 2, "Name *", self.name_var)
        self._add_entry(parent, 3, "Phone *", self.phone_var)
        self._add_entry(parent, 4, "Email", self.email_var)
        self._add_entry(parent, 5, "Company", self.company_var)
        self._add_entry(parent, 6, "Birthday", self.birthday_var)

        ttk.Label(parent, text="Address", style="FormLabel.TLabel").grid(
            row=7, column=0, sticky="nw", pady=(2, 0)
        )
        self.address_text = self._make_text(parent, height=2)
        self.address_text.grid(
            row=7, column=1, sticky="nsew", padx=(12, 0), pady=(2, 10)
        )

        ttk.Label(parent, text="Notes", style="FormLabel.TLabel").grid(
            row=8, column=0, sticky="nw", pady=(2, 0)
        )
        self.notes_text = self._make_text(parent, height=4)
        self.notes_text.grid(
            row=8, column=1, sticky="nsew", padx=(12, 0), pady=(2, 10)
        )

        ttk.Label(
            parent,
            text="Birthday uses YYYY-MM-DD.",
            style="Hint.TLabel",
        ).grid(row=9, column=1, sticky="w", padx=(12, 0), pady=(0, 4))

        actions = ttk.Frame(parent, style="Card.TFrame")
        actions.grid(row=10, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        actions.columnconfigure(1, weight=1)
        ttk.Button(
            actions,
            text="New",
            style="Secondary.TButton",
            command=self.new_contact,
        ).grid(row=0, column=0, sticky="w")
        ttk.Button(
            actions,
            text="Save Contact",
            style="Accent.TButton",
            command=self.save_contact,
        ).grid(row=0, column=2, sticky="e")

    def _add_entry(
        self, parent: ttk.Frame, row: int, label: str, variable: tk.StringVar
    ) -> ttk.Entry:
        ttk.Label(parent, text=label, style="FormLabel.TLabel").grid(
            row=row, column=0, sticky="w", pady=(0, 10)
        )
        entry = ttk.Entry(parent, textvariable=variable)
        entry.grid(
            row=row, column=1, sticky="ew", padx=(12, 0), pady=(0, 10)
        )
        return entry

    def _make_text(self, parent: ttk.Frame, height: int) -> tk.Text:
        return tk.Text(
            parent,
            height=height,
            wrap="word",
            font=(FONT, 10),
            background=CARD,
            foreground=TEXT,
            insertbackground=TEXT,
            relief="flat",
            borderwidth=0,
            highlightthickness=1,
            highlightbackground=BORDER,
            highlightcolor=ACCENT,
            padx=8,
            pady=6,
            undo=True,
        )

    def _bind_events(self) -> None:
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        self.tree.bind("<Delete>", lambda _event: self.delete_contact())
        self.search_entry.bind("<KeyRelease>", self._schedule_search)

        self.root.bind("<Control-n>", lambda _event: self.new_contact())
        self.root.bind("<Control-s>", lambda _event: self.save_contact())
        self.root.bind("<Control-f>", lambda _event: self.focus_search())
        self.root.bind("<Escape>", lambda _event: self.clear_search())
        self.root.bind("<F5>", lambda _event: self.refresh())
        self.root.protocol("WM_DELETE_WINDOW", self.close)

    def _schedule_search(self, _event: tk.Event[tk.Misc] | None = None) -> None:
        if self._search_job is not None:
            self.root.after_cancel(self._search_job)
        self._search_job = self.root.after(180, self._run_scheduled_search)

    def _run_scheduled_search(self) -> None:
        self._search_job = None
        self.refresh()

    def focus_search(self) -> None:
        self.search_entry.focus_set()
        self.search_entry.select_range(0, tk.END)

    def clear_search(self) -> None:
        if self.search_var.get():
            self.search_var.set("")
            self.refresh()
        else:
            self.search_entry.focus_set()

    def refresh(self, select_id: int | None = None) -> None:
        target_id = self.current_id if select_id is None else select_id
        search = self.search_var.get().strip()

        try:
            contacts = self.db.list_contacts(search=search)
        except ContactError as exc:
            messagebox.showerror("Could not load contacts", str(exc), parent=self.root)
            return

        self.tree.delete(*self.tree.get_children())
        for index, contact in enumerate(contacts):
            self.tree.insert(
                "",
                "end",
                iid=str(contact.id),
                values=(contact.name, contact.phone, contact.email, contact.company),
                tags=("odd",) if index % 2 else ("even",),
            )

        if target_id is not None and self.tree.exists(str(target_id)):
            item = str(target_id)
            self.tree.selection_set(item)
            self.tree.see(item)
            self._load_contact(target_id)
        else:
            self.tree.selection_remove(self.tree.selection())
            self._update_delete_button()

        if search:
            self.status_var.set(f'{len(contacts)} result(s) for "{search}"')
        else:
            self.status_var.set(f"{len(contacts)} contact(s)")

    def _on_tree_select(self, _event: tk.Event[tk.Misc] | None = None) -> None:
        selected = self.tree.selection()
        if not selected:
            self._update_delete_button()
            return
        self._load_contact(int(selected[0]))

    def _load_contact(self, contact_id: int) -> None:
        try:
            contact = self.db.get_contact(contact_id)
        except ContactError as exc:
            messagebox.showerror("Could not load contact", str(exc), parent=self.root)
            return
        if contact is None:
            self.refresh()
            return
        self._show_contact(contact)

    def _show_contact(self, contact: Contact) -> None:
        self.current_id = contact.id
        self.form_title_var.set("Contact details")
        self.name_var.set(contact.name)
        self.phone_var.set(contact.phone)
        self.email_var.set(contact.email)
        self.company_var.set(contact.company)
        self.birthday_var.set(contact.birthday)
        self._set_text(self.address_text, contact.address)
        self._set_text(self.notes_text, contact.notes)
        self._update_delete_button()

    def new_contact(self) -> None:
        self.tree.selection_remove(self.tree.selection())
        self.current_id = None
        self.form_title_var.set("New contact")
        for variable in (
            self.name_var,
            self.phone_var,
            self.email_var,
            self.company_var,
            self.birthday_var,
        ):
            variable.set("")
        self._set_text(self.address_text, "")
        self._set_text(self.notes_text, "")
        self._update_delete_button()
        self.name_entry.focus_set()
        self.status_var.set("Creating a new contact. Fields marked * are required.")

    def save_contact(self) -> None:
        data = {
            "name": self.name_var.get(),
            "phone": self.phone_var.get(),
            "email": self.email_var.get(),
            "company": self.company_var.get(),
            "birthday": self.birthday_var.get(),
            "address": self.address_text.get("1.0", "end-1c"),
            "notes": self.notes_text.get("1.0", "end-1c"),
        }

        try:
            if self.current_id is None:
                contact = self.db.create_contact(**data)
                message = f"Added {contact.name} to your contacts."
            else:
                contact = self.db.update_contact(self.current_id, **data)
                message = f"Saved changes to {contact.name}."
        except ContactError as exc:
            messagebox.showerror("Could not save contact", str(exc), parent=self.root)
            return
        except sqlite3.Error as exc:
            messagebox.showerror("Database error", str(exc), parent=self.root)
            return

        self.search_var.set("")
        self.current_id = contact.id
        self.refresh(select_id=contact.id)
        self.status_var.set(message)

    def delete_contact(self) -> None:
        if self.current_id is None:
            messagebox.showinfo(
                "No contact selected",
                "Select a contact first, then choose Delete.",
                parent=self.root,
            )
            return

        try:
            contact = self.db.get_contact(self.current_id)
        except ContactError as exc:
            messagebox.showerror("Could not load contact", str(exc), parent=self.root)
            return
        if contact is None:
            self.current_id = None
            self.new_contact()
            self.refresh()
            return

        confirmed = messagebox.askyesno(
            "Delete contact",
            f"Delete {contact.name}?\n\nThis action cannot be undone.",
            icon="warning",
            parent=self.root,
        )
        if not confirmed:
            return

        try:
            self.db.delete_contact(contact.id)
        except ContactError as exc:
            messagebox.showerror("Could not delete contact", str(exc), parent=self.root)
            return
        except sqlite3.Error as exc:
            messagebox.showerror("Database error", str(exc), parent=self.root)
            return

        self.current_id = None
        self.new_contact()
        self.refresh()
        self.status_var.set(f"Deleted {contact.name}.")

    def _update_delete_button(self) -> None:
        if self.current_id is None:
            self.delete_button.state(["disabled"])
        else:
            self.delete_button.state(["!disabled"])

    @staticmethod
    def _set_text(widget: tk.Text, value: str) -> None:
        widget.delete("1.0", "end")
        widget.insert("1.0", value)

    def close(self) -> None:
        self.root.destroy()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="contact-book",
        description="Open the Contact Book desktop application.",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_DB_PATH,
        metavar="FILE",
        help=f"SQLite database file (default: {DEFAULT_DB_PATH.name})",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = tk.Tk()

    try:
        database = ContactDatabase(args.db)
    except (sqlite3.Error, OSError) as exc:
        root.withdraw()
        messagebox.showerror("Contact Book", f"Could not open the database:\n{exc}")
        root.destroy()
        return 1

    ContactBookApp(root, database)
    try:
        root.mainloop()
    finally:
        database.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
