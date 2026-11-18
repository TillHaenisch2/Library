"""Use Case US-5: Vorbestellung, FIFO-Warteschlange & Stornierung (FR-4)."""

from __future__ import annotations

from ssa_terminal.application.auth_service import AuthService
from ssa_terminal.application.ports import LMSPort, LocalStatePort, NotificationPort
from ssa_terminal.domain.errors import BookNotLoanableError, DomainError
from ssa_terminal.domain.models import BookReservedEvent


class ReservationService:
    """Verwaltet Vormerkungen und Stornierungen am Terminal."""

    def __init__(
        self,
        auth_service: AuthService,
        lms_port: LMSPort,
        state_port: LocalStatePort,
        notification_port: NotificationPort,
    ) -> None:
        self._auth = auth_service
        self._lms = lms_port
        self._state = state_port
        self._notify = notification_port

    def reserve_book(self, book_id: str) -> BookReservedEvent:
        """Reiht den angemeldeten Benutzer in die Warteschlange ein (AC 5.1–5.7)."""
        user = self._auth.current_user
        if user is None:
            raise DomainError("Bitte melden Sie sich zuerst mit Ihrem Ausweis an.")

        self._auth.touch()

        book = self._lms.get_book(book_id)
        if book is None:
            raise BookNotLoanableError(
                f"Buch '{book_id}' wurde im Katalog nicht gefunden.", book_id=book_id
            )

        try:
            event = book.reserve(user)
            self._lms.save_books([book])
            self._notify.notify_reservation_confirmed(
                user.user_id, event.queue_position
            )
        except DomainError as err:
            self._state.log_audit(
                "RESERVATION_FAILED", user.user_id, f"{err.code}: {err.message}"
            )
            raise

        self._state.log_audit(
            "RESERVATION_SUCCESS",
            user.user_id,
            f"Buch={book.book_id}, Position={event.queue_position}",
        )
        return event

    def cancel_reservation(self, book_id: str) -> None:
        """Storniert eine bestehende Vormerkung des angemeldeten Benutzers (FR-4.5)."""
        user = self._auth.current_user
        if user is None:
            raise DomainError("Bitte melden Sie sich zuerst mit Ihrem Ausweis an.")

        self._auth.touch()

        book = self._lms.get_book(book_id)
        if book is None:
            raise BookNotLoanableError(
                f"Buch '{book_id}' wurde im Katalog nicht gefunden.", book_id=book_id
            )

        try:
            book.cancel_reservation(user)
            self._lms.save_books([book])
        except DomainError as err:
            self._state.log_audit(
                "RESERVATION_CANCEL_FAILED",
                user.user_id,
                f"{err.code}: {err.message}",
            )
            raise

        self._state.log_audit(
            "RESERVATION_CANCELLED", user.user_id, f"Buch={book.book_id}"
        )
