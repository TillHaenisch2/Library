"""Driven Ports (Interfaces) der Self-Service-Ausleihe."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Protocol

from ssa_terminal.domain.models import Book, User


@dataclass(frozen=True)
class CheckoutItemResult:
    """Ergebnis je ausgeliehenem Buch (DSGVO-konform ohne Fremddaten)."""

    book_id: str
    title: str
    due_date: date | None


class RFIDReaderPort(Protocol):
    """Kapselt den HF-RFID-Reader (ISO 15693, bis zu 5 Bücher, EAS/AFI)."""

    def get_scanned_book_ids(self) -> list[str]:
        """Liefert die aktuell auf der Scannermatte liegenden Buch-IDs."""
        ...

    def disable_eas(self, book_ids: list[str]) -> None:
        """Deaktiviert den Diebstahlschutz auf den RFID-Tags (FR-5.1)."""
        ...

    def clear_scanned_books(self) -> None:
        """Setzt die Ablagefläche im Simulator zurück."""
        ...


class LMSPort(Protocol):
    """Kapselt die Kommunikation mit dem Bibliotheksmanagementsystem (Horizon)."""

    def get_book(self, book_id: str) -> Book | None:
        ...

    def get_books(self, book_ids: list[str]) -> list[Book]:
        ...

    def get_user_borrowed_count(self, user_id: str) -> int:
        ...

    def save_books(self, books: list[Book]) -> None:
        """Persistiert aktualisierte Buchzustände im LMS."""
        ...

    def increment_user_borrowed_count(self, user_id: str, delta: int) -> None:
        ...


class IdMPort(Protocol):
    """Löst die per RFID gelesene Karten-ID auf Benutzer und Rolle auf (FR-1.1)."""

    def resolve_user_by_card(self, card_id: str) -> User | None:
        ...


class LocalStatePort(Protocol):
    """Verwaltet aktive Terminal-Sitzungen (US-6) und das Audit-Log (NFR-S3)."""

    def acquire_session(self, user_id: str, terminal_id: str) -> bool:
        """Reserviert eine exklusive Sitzung für den Benutzer (AC 6.1)."""
        ...

    def release_session(self, user_id: str, terminal_id: str) -> None:
        """Gibt die Sitzung bei Abmeldung oder Timeout frei (AC 6.2)."""
        ...

    def is_session_active(self, user_id: str, terminal_id: str) -> bool:
        ...

    def log_audit(self, event_type: str, user_id: str | None, details: str) -> None:
        """Schreibt manipulationssichere Audit-Einträge (NFR-S3)."""
        ...


class NotificationPort(Protocol):
    """Versendet Benachrichtigungen ohne Buchtitel gemäß DSGVO (FR-4.3, NFR-D3)."""

    def notify_reservation_confirmed(self, user_id: str, queue_position: int) -> None:
        ...

    def notify_pickup_ready(self, user_id: str) -> None:
        ...
