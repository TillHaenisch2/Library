"""Domain-Modelle und Zustandsmaschine für Bücher und Benutzer."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum

from ssa_terminal.domain.errors import (
    AlreadyBorrowedByUserError,
    AlreadyBorrowedError,
    AlreadyInQueueError,
    AlreadyReadyForPickupError,
    BookIsAvailableError,
    BookIsReferenceOnlyError,
    BookNotLoanableError,
    NotInQueueError,
    ReservationNotAllowedError,
    ReservedForAnotherUserError,
)


class UserRole(str, Enum):
    STUDENT = "Student"
    PROFESSOR = "Professor"


class BookState(str, Enum):
    AVAILABLE = "Available"              # Reguläres Regal (NormalShelf)
    REFERENCE_SECTION = "ReferenceSection"  # Präsenzbestand / Handapparat
    BORROWED = "Borrowed"                # Ausgeliehen
    OVERDUE = "Overdue"                  # Leihfrist überschritten
    RETURNED = "Returned"                # Zurückgegeben, noch nicht eingestellt
    READY_FOR_PICKUP = "ReadyForPickup"  # Liegt im Abholregal für holder bereit
    DAMAGED = "Damaged"                  # Beschädigt
    LOST = "Lost"                        # Verloren / nicht auffindbar
    IN_PROCESSING = "InProcessing"       # Geschäftsgang / Buchbinder


@dataclass
class User:
    user_id: str
    card_id: str
    name: str
    role: UserRole
    borrowed_count: int = 0


@dataclass(frozen=True)
class BookReservedEvent:
    book_id: str
    user_id: str
    queue_position: int  # 1-basiert (AC 5.1 / AC 5.2)


@dataclass
class Book:
    book_id: str
    title: str
    state: BookState = BookState.AVAILABLE
    borrower_id: str | None = None
    due_date: date | None = None
    holder_id: str | None = None       # Berechtigter Abholer bei READY_FOR_PICKUP
    pickup_deadline: date | None = None
    queue: list[str] = field(default_factory=list)  # FIFO-Warteschlange (user_ids)

    def validate_checkout(self, user: User) -> None:
        """Prüft FR-2.1 bis FR-2.4 ohne Zustandsänderung (für Alles-oder-Nichts)."""
        if self.state == BookState.REFERENCE_SECTION:
            raise BookIsReferenceOnlyError(
                "Buch gehört zum Präsenzbestand.", book_id=self.book_id
            )

        if self.state in (BookState.BORROWED, BookState.OVERDUE):
            raise AlreadyBorrowedError(
                "Buch ist bereits ausgeliehen.", book_id=self.book_id
            )

        if self.state == BookState.READY_FOR_PICKUP:
            if self.holder_id != user.user_id:
                raise ReservedForAnotherUserError(
                    "Buch ist für einen anderen Benutzer reserviert.",
                    book_id=self.book_id,
                )
            return

        if self.state != BookState.AVAILABLE:
            raise BookNotLoanableError(
                f"Buch im Zustand '{self.state.value}' nicht ausleihbar.",
                book_id=self.book_id,
            )

    def checkout(self, user: User, due_date: date | None) -> None:
        """Überführt das Buch in BORROWED (FR-2.1, FR-2.4, FR-4.4)."""
        self.validate_checkout(user)
        self.state = BookState.BORROWED
        self.borrower_id = user.user_id
        self.due_date = due_date
        self.holder_id = None
        self.pickup_deadline = None

    def reserve(self, user: User) -> BookReservedEvent:
        """Interne Transition reservieren(u) gemäß US-5 & Zustandsmodell."""
        if self.state == BookState.AVAILABLE:
            raise BookIsAvailableError(
                "Buch ist frei verfügbar im Regal.", book_id=self.book_id
            )

        if self.state == BookState.REFERENCE_SECTION:
            raise BookIsReferenceOnlyError(
                "Präsenzbestand kann nicht reserviert werden.", book_id=self.book_id
            )

        if self.state == BookState.READY_FOR_PICKUP and self.holder_id == user.user_id:
            raise AlreadyReadyForPickupError(
                "Buch liegt bereits für Sie im Abholregal bereit.",
                book_id=self.book_id,
            )

        if self.state in (BookState.BORROWED, BookState.OVERDUE) and self.borrower_id == user.user_id:
            raise AlreadyBorrowedByUserError(
                "Sie haben dieses Buch bereits selbst ausgeliehen.",
                book_id=self.book_id,
            )

        if self.state not in (
            BookState.BORROWED,
            BookState.OVERDUE,
            BookState.READY_FOR_PICKUP,
        ):
            raise ReservationNotAllowedError(
                f"Reservierung im Zustand '{self.state.value}' nicht möglich.",
                book_id=self.book_id,
            )

        if user.user_id in self.queue:
            raise AlreadyInQueueError(
                "Sie stehen für dieses Buch bereits in der Warteschlange.",
                book_id=self.book_id,
            )

        self.queue.append(user.user_id)
        return BookReservedEvent(
            book_id=self.book_id,
            user_id=user.user_id,
            queue_position=len(self.queue),
        )

    def cancel_reservation(self, user: User) -> None:
        """Storniert eine bestehende Vormerkung (FR-4.5)."""
        if user.user_id not in self.queue:
            raise NotInQueueError(
                "Keine aktive Vormerkung für dieses Buch vorhanden.",
                book_id=self.book_id,
            )
        self.queue.remove(user.user_id)
