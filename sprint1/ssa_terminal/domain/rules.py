"""Konfigurierbare Geschäftsregeln für Ausleihlimits und Leihfristen."""

from dataclasses import dataclass
from datetime import date, timedelta

from ssa_terminal.domain.errors import (
    DomainError,
    MaxBooksLimitReachedError,
    MultipleBooksValidationError,
)
from ssa_terminal.domain.models import Book, User, UserRole


@dataclass(frozen=True)
class PolicyConfig:
    """Konfigurierbare Geschäftsparameter gemäß NFR-M1."""

    student_max_books: int = 10
    student_loan_days: int = 28
    pickup_hold_days: int = 7
    max_books_per_scan: int = 5  # NFR-P2


class LoanPolicy:
    """Prüft Ausleihberechtigungen und berechnet Fälligkeitsdaten."""

    def __init__(self, config: PolicyConfig | None = None) -> None:
        self.config = config or PolicyConfig()

    def calculate_due_date(self, role: UserRole, checkout_date: date) -> date | None:
        """FR-3.1 (Student: +28 Tage) & FR-3.2 (Professor: None)."""
        if role == UserRole.STUDENT:
            return checkout_date + timedelta(days=self.config.student_loan_days)
        if role == UserRole.PROFESSOR:
            return None
        raise ValueError(f"Unbekannte Benutzerrolle: {role}")

    def max_books_for_role(self, role: UserRole) -> int | None:
        """FR-1.2 (Student: max. 10) & FR-1.3 (Professor: unbegrenzt)."""
        if role == UserRole.STUDENT:
            return self.config.student_max_books
        if role == UserRole.PROFESSOR:
            return None
        raise ValueError(f"Unbekannte Benutzerrolle: {role}")

    def validate_batch_checkout(self, user: User, books: list[Book]) -> None:
        """Prüft alle aufgelegten Bücher nach dem Alles-oder-Nichts-Prinzip (UC-1 1a/1b)."""
        if not books:
            return

        # 1. Limitprüfung (FR-1.2, FR-3.3, AC 1.2, AC 1.3)
        max_books = self.max_books_for_role(user.role)
        if max_books is not None and (user.borrowed_count + len(books)) > max_books:
            raise MaxBooksLimitReachedError(
                f"Maximales Limit von {max_books} Büchern erreicht "
                f"(aktuell: {user.borrowed_count}, neu: {len(books)})."
            )

        # 2. Einzelprüfung aller Bücher sammeln, damit bei Mehrfachausleihe
        # alle betroffenen Bücher gemeldet werden können (UC-1 Extension 1b)
        book_errors: list[DomainError] = []
        for book in books:
            try:
                book.validate_checkout(user)
            except DomainError as err:
                book_errors.append(err)

        if len(book_errors) == 1:
            raise book_errors[0]
        if len(book_errors) > 1:
            raise MultipleBooksValidationError(book_errors)
