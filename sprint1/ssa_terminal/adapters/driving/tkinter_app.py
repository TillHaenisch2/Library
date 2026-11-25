"""Tkinter Driving Adapter mit Test-Harness (links/mitte) & Terminal-Screen (unten)."""

from __future__ import annotations

from datetime import datetime
import tkinter as tk
from tkinter import ttk

from ssa_terminal.adapters.driven.mocks import SimulatedRFIDAdapter, SimulationContext
from ssa_terminal.application.auth_service import AuthService
from ssa_terminal.application.checkout_service import CheckoutService
from ssa_terminal.application.reserve_service import ReservationService
from ssa_terminal.domain.errors import (
    AlreadyBorrowedError,
    DomainError,
    MultipleBooksValidationError,
)
from ssa_terminal.domain.models import Book, BookState


class SSATerminalApp:
    """GUI des Walking Skeletons gemäß ADR001_4 und ADR003_4."""

    def __init__(
        self,
        root: tk.Tk,
        ctx: SimulationContext,
        rfid_adapter: SimulatedRFIDAdapter,
        auth_service: AuthService,
        checkout_service: CheckoutService,
        reserve_service: ReservationService,
    ) -> None:
        self._root = root
        self._ctx = ctx
        self._rfid = rfid_adapter
        self._auth = auth_service
        self._checkout = checkout_service
        self._reserve = reserve_service

        self._book_buttons: dict[str, tk.Button] = {}
        self._user_buttons: dict[str, tk.Button] = {}
        self._last_failed_book_ids: list[str] = []

        self._root.title("Bibliothek Self-Service-Ausleihe – Walking Skeleton (Sprint 1)")
        self._root.geometry("1280x860")

        self._build_layout()
        self._refresh_all()
        self._write_terminal(
            "Willkommen an der Self-Service-Ausleihe.\n"
            "Bitte legen Sie Ihren Bibliotheksausweis auf (links Benutzer wählen).",
            level="info",
            clear=True,
        )
        self._schedule_timeout_check()

    def _build_layout(self) -> None:
        top_frame = ttk.Frame(self._root, padding=10)
        top_frame.pack(fill=tk.BOTH, expand=True)

        # --- Linkes Panel: Benutzer & Session-Steuerung ---
        left_frame = ttk.LabelFrame(
            top_frame, text="Test-Harness: Ausweise & Sitzung", padding=10
        )
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))

        for card_id in self._ctx.users_by_card:
            btn = tk.Button(
                left_frame,
                text="",
                width=26,
                anchor="w",
                padx=8,
                pady=6,
                command=lambda cid=card_id: self._on_scan_card(cid),
            )
            btn.pack(fill=tk.X, pady=3)
            self._user_buttons[card_id] = btn

        ttk.Separator(left_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)

        tk.Button(
            left_frame,
            text="Abmelden",
            bg="#f0ad4e",
            fg="#000000",
            pady=6,
            command=self._on_logout,
        ).pack(fill=tk.X, pady=3)

        tk.Button(
            left_frame,
            text="Reset (Anfangszustand)",
            bg="#d9534f",
            fg="#000000",
            pady=6,
            command=self._on_reset,
        ).pack(fill=tk.X, pady=3)

        # --- Mittleres Panel: Bücher-Toggles (20 Stück) ---
        center_frame = ttk.LabelFrame(
            top_frame,
            text="Test-Harness: Bücher-Ablage (Klick = auf Scanner legen / herunternehmen)",
            padding=10,
        )
        center_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        grid_frame = ttk.Frame(center_frame)
        grid_frame.pack(fill=tk.BOTH, expand=True)

        for idx, book_id in enumerate(sorted(self._ctx.books.keys())):
            row, col = divmod(idx, 2)
            btn = tk.Button(
                grid_frame,
                text="",
                anchor="w",
                justify=tk.LEFT,
                padx=8,
                pady=5,
                command=lambda bid=book_id: self._on_toggle_book(bid),
            )
            btn.grid(row=row, column=col, sticky="nsew", padx=4, pady=3)
            grid_frame.columnconfigure(col, weight=1)
            grid_frame.rowconfigure(row, weight=1)
            self._book_buttons[book_id] = btn

        # --- Unteres Panel: Simuliertes Terminal-Fenster (schwarzer Hintergrund) ---
        bottom_frame = ttk.LabelFrame(
            self._root,
            text="Simuliertes Terminal-Display (Realer Output – DSGVO-geprüft nach NFR-D2)",
            padding=10,
        )
        bottom_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=(0, 10))

        action_bar = ttk.Frame(bottom_frame)
        action_bar.pack(fill=tk.X, pady=(0, 8))

        tk.Button(
            action_bar,
            text="Ausleihe starten",
            bg="#2e7d32",
            fg="#000000",
            font=("TkDefaultFont", 11, "bold"),
            padx=16,
            pady=6,
            command=self._on_checkout,
        ).pack(side=tk.LEFT, padx=(0, 8))

        tk.Button(
            action_bar,
            text="Aufgelegte(s) Buch/Bücher vormerken",
            bg="#1565c0",
            fg="#000000",
            padx=12,
            pady=6,
            command=self._on_reserve,
        ).pack(side=tk.LEFT, padx=(0, 8))

        tk.Button(
            action_bar,
            text="Vormerkung stornieren",
            bg="#546e7a",
            fg="#000000",
            padx=12,
            pady=6,
            command=self._on_cancel_reservation,
        ).pack(side=tk.LEFT)

        text_container = ttk.Frame(bottom_frame)
        text_container.pack(fill=tk.X)

        scrollbar = ttk.Scrollbar(text_container, orient=tk.VERTICAL)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self._terminal_text = tk.Text(
            text_container,
            height=12,
            bg="#111111",
            fg="#33ff66",
            insertbackground="#33ff66",
            font=("Monospace", 11),
            state=tk.DISABLED,
            padx=10,
            pady=8,
            yscrollcommand=scrollbar.set,
        )
        self._terminal_text.pack(side=tk.LEFT, fill=tk.X, expand=True)
        scrollbar.config(command=self._terminal_text.yview)

        # Farb-Tags für Meldungsarten
        self._terminal_text.tag_configure("info", foreground="#33ff66")
        self._terminal_text.tag_configure("success", foreground="#69f0ae")
        self._terminal_text.tag_configure("error", foreground="#ff5252")
        self._terminal_text.tag_configure("warn", foreground="#ffd740")
        self._terminal_text.tag_configure("meta", foreground="#90a4ae")

    # --- Event-Handler ---

    def _on_scan_card(self, card_id: str) -> None:
        try:
            user = self._auth.login_with_card(card_id)
            limit_info = (
                f"Aktuell ausgeliehen: {user.borrowed_count}/10 Bücher"
                if user.role.value == "Student"
                else "Ausleihlimit: unbegrenzt"
            )
            self._write_terminal(
                f"Anmeldung erfolgreich: {user.name.split(' (')[0]} ({user.role.value})\n"
                f"{limit_info}\n"
                "Legen Sie Ihre Bücher auf die Ablage und drücken Sie 'Ausleihe starten'.",
                level="success",
            )
        except DomainError as err:
            self._write_terminal(f"[FEHLER {err.code}] {err.message}", level="error")
        except Exception as exc:
            self._write_terminal(f"[SYSTEMFEHLER] {exc}", level="error")
        self._refresh_all()

    def _on_toggle_book(self, book_id: str) -> None:
        placed = self._rfid.toggle_book(book_id)
        self._auth.touch()
        book = self._ctx.books[book_id]
        count = len(self._rfid.get_scanned_book_ids())
        action = "auf Scanner gelegt" if placed else "vom Scanner genommen"
        # DSGVO NFR-D2: nur Buch-ID/Titel des aufgelegten Buchs, keine Ausleiherdaten
        self._write_terminal(
            f"Scanner: [{book.book_id}] {book.title} {action} (aktuell {count}/5 auf Ablage).",
            level="info",
        )
        self._refresh_all()

    def _on_checkout(self) -> None:
        self._last_failed_book_ids.clear()
        scanned = self._rfid.get_scanned_book_ids()
        if not scanned:
            self._write_terminal(
                "[HINWEIS] Keine Bücher auf der Ablage erkannt. "
                "Bitte legen Sie mindestens ein Buch auf den Scanner.",
                level="warn",
            )
            return

        try:
            results = self._checkout.checkout_scanned_books()
            lines = [f"Ausleihe erfolgreich ({len(results)} Medium/Medien):"]
            for item in results:
                due_str = (
                    item.due_date.strftime("%d.%m.%Y")
                    if item.due_date
                    else "unbegrenzt (kein Fälligkeitsdatum)"
                )
                lines.append(f"  - [{item.book_id}] {item.title} | Rückgabe bis: {due_str}")
            lines.append("Diebstahlschutz deaktiviert. Sie können die Bücher nun mitnehmen.")
            self._write_terminal("\n".join(lines), level="success")
            self._rfid.clear_scanned_books()

        except MultipleBooksValidationError as multi_err:
            lines = [
                "[FEHLER] Ausleihe abgebrochen (Alles-oder-Nichts). "
                "Bitte entnehmen Sie folgende Bücher:"
            ]
            for err in multi_err.errors:
                if err.book_id:
                    self._last_failed_book_ids.append(err.book_id)
                lines.append(f"  - [{err.book_id}] {err.message} ({err.code})")
            self._write_terminal("\n".join(lines), level="error")

        except DomainError as err:
            if err.book_id:
                self._last_failed_book_ids.append(err.book_id)
            hint = ""
            if isinstance(err, AlreadyBorrowedError):
                hint = (
                    "\nHinweis: Sie können dieses Buch über "
                    "'Aufgelegte(s) Buch/Bücher vormerken' reservieren."
                )
            self._write_terminal(f"[FEHLER {err.code}] {err.message}{hint}", level="error")

        except Exception as exc:
            self._write_terminal(f"[SYSTEMFEHLER] {exc}", level="error")

        self._refresh_all()

    def _on_reserve(self) -> None:
        scanned = self._rfid.get_scanned_book_ids()
        if not scanned:
            self._write_terminal(
                "[HINWEIS] Bitte legen Sie das gewünschte Buch zur Vormerkung auf.",
                level="warn",
            )
            return

        for book_id in scanned:
            try:
                event = self._reserve.reserve_book(book_id)
                self._write_terminal(
                    f"[{book_id}] Vormerkung erfolgreich – Wartelistenplatz: {event.queue_position}.",
                    level="success",
                )
            except DomainError as err:
                self._write_terminal(
                    f"[{book_id}] [FEHLER {err.code}] {err.message}",
                    level="error",
                )
            except Exception as exc:
                self._write_terminal(f"[SYSTEMFEHLER] {exc}", level="error")
        self._refresh_all()

    def _on_cancel_reservation(self) -> None:
        scanned = self._rfid.get_scanned_book_ids()
        if not scanned:
            self._write_terminal(
                "[HINWEIS] Bitte legen Sie das Buch auf, dessen Vormerkung storniert werden soll.",
                level="warn",
            )
            return

        for book_id in scanned:
            try:
                self._reserve.cancel_reservation(book_id)
                self._write_terminal(
                    f"[{book_id}] Vormerkung wurde storniert.",
                    level="success",
                )
            except DomainError as err:
                self._write_terminal(
                    f"[{book_id}] [FEHLER {err.code}] {err.message}",
                    level="error",
                )
            except Exception as exc:
                self._write_terminal(f"[SYSTEMFEHLER] {exc}", level="error")
        self._refresh_all()

    def _on_logout(self) -> None:
        if self._auth.current_user is None:
            self._write_terminal("[HINWEIS] Keine aktive Sitzung vorhanden.", level="warn")
            return
        self._auth.logout(reason="ManualLogout")
        self._rfid.clear_scanned_books()
        self._write_terminal("Sie wurden abgemeldet. Auf Wiedersehen!", level="info")
        self._refresh_all()

    def _on_reset(self) -> None:
        self._auth.logout(reason="SimulationReset")
        self._ctx.reset()
        self._last_failed_book_ids.clear()
        self._write_terminal(
            "System zurückgesetzt.\n"
            "Bitte legen Sie Ihren Bibliotheksausweis auf (links Benutzer wählen).",
            level="info",
            clear=True,
        )
        self._refresh_all()

    def _schedule_timeout_check(self) -> None:
        if self._auth.check_timeout():
            self._rfid.clear_scanned_books()
            self._write_terminal(
                "[TIMEOUT] Sitzung wegen 30 Sekunden Inaktivität automatisch beendet (NFR-S1).",
                level="warn",
            )
            self._refresh_all()
        self._root.after(1000, self._schedule_timeout_check)

    # --- UI-Darstellung aktualisieren ---

    def _refresh_all(self) -> None:
        active_user = self._auth.current_user
        for card_id, btn in self._user_buttons.items():
            user = self._ctx.users_by_card[card_id]
            is_active = active_user is not None and active_user.user_id == user.user_id
            count_txt = (
                f"{user.borrowed_count}/10"
                if user.role.value == "Student"
                else f"{user.borrowed_count}/∞"
            )
            prefix = "▶ " if is_active else ""
            btn.config(
                text=f"{prefix}{user.name.split(' (')[0]} ({user.role.value}, {count_txt})",
                bg="#cce5ff" if is_active else "#f0f0f0",
            )

        for book_id, btn in self._book_buttons.items():
            book = self._ctx.books[book_id]
            on_scanner = book_id in self._ctx.scanned_book_ids
            eas_off = book_id in self._ctx.eas_disabled_books
            btn.config(
                text=self._format_book_debug_label(book, on_scanner, eas_off),
                bg=self._book_button_color(book, on_scanner),
                relief=tk.SUNKEN if on_scanner else tk.RAISED,
            )

    @staticmethod
    def _format_book_debug_label(book: Book, on_scanner: bool, eas_off: bool) -> str:
        scan_mark = "[AUF SCANNER] " if on_scanner else ""
        eas_mark = "EAS:AUS" if eas_off else "EAS:AN"
        extra = ""
        if book.borrower_id:
            extra += f" | Ausleiher: {book.borrower_id}"
        if book.holder_id:
            extra += f" | Abholer: {book.holder_id}"
        if book.queue:
            extra += f" | Queue: {','.join(book.queue)}"
        return f"{scan_mark}{book.book_id}: {book.title}\nStatus: {book.state.value} ({eas_mark}){extra}"

    @staticmethod
    def _book_button_color(book: Book, on_scanner: bool) -> str:
        if on_scanner:
            return "#fff59d"
        if book.state == BookState.AVAILABLE:
            return "#e8f5e9"
        if book.state == BookState.READY_FOR_PICKUP:
            return "#e3f2fd"
        if book.state == BookState.REFERENCE_SECTION:
            return "#ffebee"
        return "#eeeeee"

    def _write_terminal(
        self, text: str, level: str = "info", clear: bool = False
    ) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        self._terminal_text.config(state=tk.NORMAL)
        if clear:
            self._terminal_text.delete("1.0", tk.END)
        else:
            self._terminal_text.insert(tk.END, "\n" + "-" * 72 + "\n", "meta")
        self._terminal_text.insert(tk.END, f"[{timestamp}] ", "meta")
        self._terminal_text.insert(tk.END, text + "\n", level)
        self._terminal_text.see(tk.END)
        self._terminal_text.config(state=tk.DISABLED)
