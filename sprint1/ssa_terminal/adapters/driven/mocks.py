"""In-Process-Mocks für RFID-Reader, LMS (Horizon), IdM, LocalState & Notifications."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from ssa_terminal.domain.models import Book, BookState, User, UserRole


@dataclass
class AuditEntry:
    timestamp: datetime
    event_type: str
    user_id: str | None
    details: str


@dataclass
class SimulationContext:
    """Gemeinsamer In-Memory-Zustand für das Walking Skeleton (inkl. Reset)."""

    users_by_card: dict[str, User] = field(default_factory=dict)
    books: dict[str, Book] = field(default_factory=dict)
    scanned_book_ids: set[str] = field(default_factory=set)
    eas_disabled_books: set[str] = field(default_factory=set)
    active_sessions: dict[str, str] = field(default_factory=dict)  # user_id -> terminal_id
    audit_log: list[AuditEntry] = field(default_factory=list)
    notifications: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.users_by_card and not self.books:
            self.reset()

    def reset(self) -> None:
        """Setzt alle Benutzer-, Buch- und Sitzungsdaten auf den Ausgangszustand zurück."""
        today = date.today()
        self.scanned_book_ids.clear()
        self.eas_disabled_books.clear()
        self.active_sessions.clear()
        self.audit_log.clear()
        self.notifications.clear()

        self.users_by_card = {
            "CARD-S1": User("u-anna", "CARD-S1", "Anna (Studi, 2/10)", UserRole.STUDENT, 2),
            "CARD-S2": User("u-ben", "CARD-S2", "Ben (Studi, 8/10)", UserRole.STUDENT, 8),
            "CARD-S3": User("u-clara", "CARD-S3", "Clara (Studi, 10/10)", UserRole.STUDENT, 10),
            "CARD-P1": User("u-prof", "CARD-P1", "Prof. Dr. Weber", UserRole.PROFESSOR, 14),
        }

        initial_books = [
            # Regulärer Bestand (Available)
            Book("B-01", "Clean Architecture (Martin)", BookState.AVAILABLE),
            Book("B-02", "Software Architecture in Practice", BookState.AVAILABLE),
            Book("B-03", "Designing Data-Intensive Apps", BookState.AVAILABLE),
            Book("B-04", "Domain-Driven Design", BookState.AVAILABLE),
            Book("B-05", "Python in a Nutshell", BookState.AVAILABLE),
            Book("B-06", "Patterns of Enterprise App Arch", BookState.AVAILABLE),
            Book("B-07", "Operating Systems: Three Easy Pieces", BookState.AVAILABLE),
            Book("B-08", "Computer Networking (Kurose)", BookState.AVAILABLE),
            Book("B-09", "Algorithms (Sedgewick)", BookState.AVAILABLE),
            Book("B-10", "Database Internals", BookState.AVAILABLE),
            # Präsenzbestand / Handapparat (ReferenceSection -> AC 3.1)
            Book("B-11", "Handbuch Hochschulrecht (Präsenz)", BookState.REFERENCE_SECTION),
            Book("B-12", "Brockhaus Enzyklopädie Bd. 1 (Präsenz)", BookState.REFERENCE_SECTION),
            # Bereits ausgeliehen (Borrowed -> AC 2.2, US-5 Vormerkung)
            Book(
                "B-13",
                "Refactoring (Fowler)",
                BookState.BORROWED,
                borrower_id="u-ben",
                due_date=today + timedelta(days=14),
            ),
            Book(
                "B-14",
                "The Pragmatic Programmer",
                BookState.BORROWED,
                borrower_id="u-anna",
                due_date=today + timedelta(days=20),
                queue=["u-ben"],
            ),
            Book(
                "B-15",
                "Fundamentals of Software Arch",
                BookState.BORROWED,
                borrower_id="u-prof",
                due_date=None,
            ),
            Book(
                "B-16",
                "Structure & Interpretation (SICP)",
                BookState.BORROWED,
                borrower_id="u-clara",
                due_date=today + timedelta(days=7),
            ),
            # Abholregal (ReadyForPickup -> AC 4.1, AC 4.2, AC 5.6)
            Book(
                "B-17",
                "Compilers (Dragon Book)",
                BookState.READY_FOR_PICKUP,
                holder_id="u-anna",
                pickup_deadline=today + timedelta(days=5),
            ),
            Book(
                "B-18",
                "Artificial Intelligence (Russell)",
                BookState.READY_FOR_PICKUP,
                holder_id="u-prof",
                pickup_deadline=today + timedelta(days=5),
            ),
            Book(
                "B-19",
                "Distributed Systems (Tanenbaum)",
                BookState.READY_FOR_PICKUP,
                holder_id="u-ben",
                pickup_deadline=today + timedelta(days=3),
                queue=["u-clara"],
            ),
            # Sonderzustand im Geschäftsgang
            Book("B-20", "Neuerwerbung: Rust in Action", BookState.IN_PROCESSING),
        ]
        self.books = {b.book_id: b for b in initial_books}


class SimulatedRFIDAdapter:
    """Implementiert RFIDReaderPort über die Toggle-Buttons der Simulator-GUI."""

    def __init__(self, ctx: SimulationContext) -> None:
        self._ctx = ctx

    def toggle_book(self, book_id: str) -> bool:
        """Legt ein Buch auf den Scanner oder nimmt es herunter."""
        if book_id in self._ctx.scanned_book_ids:
            self._ctx.scanned_book_ids.remove(book_id)
            return False
        self._ctx.scanned_book_ids.add(book_id)
        return True

    def get_scanned_book_ids(self) -> list[str]:
        return sorted(self._ctx.scanned_book_ids)

    def disable_eas(self, book_ids: list[str]) -> None:
        self._ctx.eas_disabled_books.update(book_ids)

    def clear_scanned_books(self) -> None:
        self._ctx.scanned_book_ids.clear()


class InMemoryLMSAdapter:
    """Implementiert LMSPort gegen das In-Memory-Dictionary."""

    def __init__(self, ctx: SimulationContext) -> None:
        self._ctx = ctx

    def get_book(self, book_id: str) -> Book | None:
        book = self._ctx.books.get(book_id)
        return deepcopy(book) if book else None

    def get_books(self, book_ids: list[str]) -> list[Book]:
        return [deepcopy(self._ctx.books[bid]) for bid in book_ids if bid in self._ctx.books]

    def get_user_borrowed_count(self, user_id: str) -> int:
        for user in self._ctx.users_by_card.values():
            if user.user_id == user_id:
                return user.borrowed_count
        return 0

    def save_books(self, books: list[Book]) -> None:
        for book in books:
            self._ctx.books[book.book_id] = deepcopy(book)

    def increment_user_borrowed_count(self, user_id: str, delta: int) -> None:
        for user in self._ctx.users_by_card.values():
            if user.user_id == user_id:
                user.borrowed_count += delta
                return


class InMemoryIdMAdapter:
    """Implementiert IdMPort gegen die Test-Benutzer."""

    def __init__(self, ctx: SimulationContext) -> None:
        self._ctx = ctx

    def resolve_user_by_card(self, card_id: str) -> User | None:
        user = self._ctx.users_by_card.get(card_id)
        return deepcopy(user) if user else None


class InMemoryStateAdapter:
    """Implementiert LocalStatePort für Terminal-Sitzungen und Audit-Logs."""

    def __init__(self, ctx: SimulationContext) -> None:
        self._ctx = ctx

    def acquire_session(self, user_id: str, terminal_id: str) -> bool:
        existing = self._ctx.active_sessions.get(user_id)
        if existing is not None and existing != terminal_id:
            return False
        self._ctx.active_sessions[user_id] = terminal_id
        return True

    def release_session(self, user_id: str, terminal_id: str) -> None:
        if self._ctx.active_sessions.get(user_id) == terminal_id:
            del self._ctx.active_sessions[user_id]

    def is_session_active(self, user_id: str, terminal_id: str) -> bool:
        return self._ctx.active_sessions.get(user_id) == terminal_id

    def log_audit(self, event_type: str, user_id: str | None, details: str) -> None:
        self._ctx.audit_log.append(
            AuditEntry(
                timestamp=datetime.now(),
                event_type=event_type,
                user_id=user_id,
                details=details,
            )
        )


class ConsoleNotificationAdapter:
    """Implementiert NotificationPort für Benachrichtigungs-Events (DSGVO-konform)."""

    def __init__(self, ctx: SimulationContext) -> None:
        self._ctx = ctx

    def notify_reservation_confirmed(self, user_id: str, queue_position: int) -> None:
        msg = f"[Notify -> {user_id}] Vormerkung bestätigt (Wartelistenplatz {queue_position})."
        self._ctx.notifications.append(msg)

    def notify_pickup_ready(self, user_id: str) -> None:
        msg = f"[Notify -> {user_id}] Ein vorgemerktes Medium liegt im Abholregal bereit."
        self._ctx.notifications.append(msg)
