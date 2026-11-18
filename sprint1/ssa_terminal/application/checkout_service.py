"""Use Case UC-1: Self-Service Buch ausleihen (Einzel- und Mehrfachausleihe)."""

from __future__ import annotations

from datetime import date

from ssa_terminal.application.auth_service import AuthService
from ssa_terminal.application.ports import (
    CheckoutItemResult,
    LMSPort,
    LocalStatePort,
    RFIDReaderPort,
)
from ssa_terminal.domain.errors import BookNotLoanableError, DomainError
from ssa_terminal.domain.models import UserRole
from ssa_terminal.domain.rules import LoanPolicy


class CheckoutService:
    """Führt Ausleihvorgänge nach dem Alles-oder-Nichts-Prinzip durch."""

    def __init__(
        self,
        auth_service: AuthService,
        rfid_port: RFIDReaderPort,
        lms_port: LMSPort,
        state_port: LocalStatePort,
        policy: LoanPolicy | None = None,
    ) -> None:
        self._auth = auth_service
        self._rfid = rfid_port
        self._lms = lms_port
        self._state = state_port
        self._policy = policy or LoanPolicy()

    def checkout_scanned_books(
        self, today: date | None = None
    ) -> list[CheckoutItemResult]:
        """Leiht alle aktuell auf der RFID-Ablage liegenden Bücher aus (UC-1)."""
        user = self._auth.current_user
        if user is None:
            raise DomainError("Bitte melden Sie sich zuerst mit Ihrem Ausweis an.")

        self._auth.touch()
        today = today or date.today()

        book_ids = self._rfid.get_scanned_book_ids()
        if not book_ids:
            return []

        if len(book_ids) > self._policy.config.max_books_per_scan:
            raise DomainError(
                f"Es können maximal {self._policy.config.max_books_per_scan} Bücher "
                "gleichzeitig aufgelegt werden."
            )

        books = self._lms.get_books(book_ids)
        if len(books) != len(book_ids):
            found_ids = {b.book_id for b in books}
            missing = [bid for bid in book_ids if bid not in found_ids]
            self._state.log_audit(
                "CHECKOUT_FAILED", user.user_id, f"Unbekannte Buch-IDs: {missing}"
            )
            raise BookNotLoanableError(
                f"Unbekanntes Medium erkannt: {', '.join(missing)}",
                book_id=missing[0],
            )

        # Aktuelles Kontingent vor der Validierung frisch abrufen
        user.borrowed_count = self._lms.get_user_borrowed_count(user.user_id)

        try:
            # 1. Alles-oder-Nichts-Validierung aller Bücher (UC-1 1a/1b)
            self._policy.validate_batch_checkout(user, books)

            # 2. Zustandsübergänge berechnen (FR-3.1, FR-3.2, UC-1 Schritt 4 & 5)
            due_date = self._policy.calculate_due_date(user.role, today)
            results: list[CheckoutItemResult] = []
            for book in books:
                book.checkout(user, due_date)
                results.append(
                    CheckoutItemResult(
                        book_id=book.book_id,
                        title=book.title,
                        due_date=book.due_date,
                    )
                )

            # 3. Atomare Ausführung: LMS buchen + Diebstahlschutz deaktivieren (NFR-R1)
            self._lms.save_books(books)
            if user.role == UserRole.STUDENT:
                self._lms.increment_user_borrowed_count(user.user_id, len(books))
                user.borrowed_count += len(books)

            self._rfid.disable_eas([b.book_id for b in books])

        except DomainError as err:
            self._state.log_audit(
                "CHECKOUT_FAILED", user.user_id, f"{err.code}: {err.message}"
            )
            raise

        self._state.log_audit(
            "CHECKOUT_SUCCESS",
            user.user_id,
            f"Ausgeliehen: {[r.book_id for r in results]}, DueDate={due_date}",
        )
        return results
