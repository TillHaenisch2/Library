"""Fachliche Exceptions der Self-Service-Ausleihe."""


class DomainError(Exception):
    """Basisklasse für alle fachlichen Regelverletzungen."""

    code: str = "DomainError"

    def __init__(self, message: str, book_id: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.book_id = book_id


# --- Authentifizierung & Sitzung (US-6) ---

class UserNotFoundError(DomainError):
    code = "UserNotFound"


class AlreadyLoggedInElsewhereError(DomainError):
    code = "AlreadyLoggedInElsewhere"


# --- Ausleihe (UC-1, US-1 bis US-4) ---

class MaxBooksLimitReachedError(DomainError):
    code = "MaxBooksLimitReached"


class BookIsReferenceOnlyError(DomainError):
    code = "BookIsReferenceOnly"


class AlreadyBorrowedError(DomainError):
    code = "AlreadyBorrowed"


class ReservedForAnotherUserError(DomainError):
    code = "ReservedForAnotherUser"


class BookNotLoanableError(DomainError):
    code = "BookNotLoanable"


class MultipleBooksValidationError(DomainError):
    """Bündelt Einzelfehler bei Mehrfachausleihe (Alles-oder-Nichts, UC-1 1b)."""

    code = "MultipleBooksValidationFailed"

    def __init__(self, errors: list[DomainError]) -> None:
        self.errors = errors
        details = "; ".join(f"{e.book_id or '?'}: {e.code}" for e in errors)
        super().__init__(f"Ausleihe abgebrochen: {details}")


# --- Reservierung & Warteschlange (US-5) ---

class AlreadyInQueueError(DomainError):
    code = "AlreadyInQueue"


class BookIsAvailableError(DomainError):
    code = "BookIsAvailable"


class AlreadyReadyForPickupError(DomainError):
    code = "AlreadyReadyForPickup"


class AlreadyBorrowedByUserError(DomainError):
    code = "AlreadyBorrowedByUser"


class ReservationNotAllowedError(DomainError):
    code = "ReservationNotAllowed"


class NotInQueueError(DomainError):
    code = "NotInQueue"
