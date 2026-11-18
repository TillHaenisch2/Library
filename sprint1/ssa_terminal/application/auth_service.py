"""Sitzungs- und Authentifizierungs-Service (FR-1.1, US-6, NFR-S1)."""

from __future__ import annotations

from datetime import datetime, timedelta

from ssa_terminal.application.ports import IdMPort, LMSPort, LocalStatePort
from ssa_terminal.domain.errors import AlreadyLoggedInElsewhereError, UserNotFoundError
from ssa_terminal.domain.models import User


class AuthService:
    """Verwaltet die Anmeldung, aktive Sitzung und den 30s-Timeout an einem Terminal."""

    def __init__(
        self,
        idm_port: IdMPort,
        lms_port: LMSPort,
        state_port: LocalStatePort,
        terminal_id: str = "TERM-01",
        session_timeout_seconds: int = 30,
    ) -> None:
        self._idm = idm_port
        self._lms = lms_port
        self._state = state_port
        self._terminal_id = terminal_id
        self._timeout = timedelta(seconds=session_timeout_seconds)
        self._current_user: User | None = None
        self._last_activity: datetime | None = None

    @property
    def current_user(self) -> User | None:
        return self._current_user

    def login_with_card(self, card_id: str, now: datetime | None = None) -> User:
        """Authentifiziert einen Benutzer per Ausweis-ID (FR-1.1, AC 6.1, AC 6.2)."""
        now = now or datetime.now()

        # Falls an diesem Terminal noch eine alte Sitzung aktiv war, sauber beenden
        if self._current_user is not None:
            self.logout(reason="UserSwitched")

        user = self._idm.resolve_user_by_card(card_id)
        if user is None:
            self._state.log_audit("LOGIN_FAILED", None, f"Unbekannte Karte: {card_id}")
            raise UserNotFoundError(f"Ausweis '{card_id}' nicht erkannt.")

        if not self._state.acquire_session(user.user_id, self._terminal_id):
            self._state.log_audit(
                "LOGIN_REJECTED",
                user.user_id,
                f"Bereits an anderem Terminal aktiv (abgelehnt an {self._terminal_id})",
            )
            raise AlreadyLoggedInElsewhereError(
                "Sie sind bereits an einem anderen Terminal angemeldet."
            )

        # Aktuelles Ausleihkontingent aus dem LMS synchronisieren
        user.borrowed_count = self._lms.get_user_borrowed_count(user.user_id)
        self._current_user = user
        self._last_activity = now
        self._state.log_audit(
            "LOGIN_SUCCESS", user.user_id, f"Rolle={user.role.value}, Terminal={self._terminal_id}"
        )
        return user

    def touch(self, now: datetime | None = None) -> None:
        """Aktualisiert den Zeitstempel der letzten Benutzeraktion."""
        if self._current_user is not None:
            self._last_activity = now or datetime.now()

    def check_timeout(self, now: datetime | None = None) -> bool:
        """Prüft NFR-S1 (30s Inaktivität) und meldet bei Überschreitung ab."""
        if self._current_user is None or self._last_activity is None:
            return False

        now = now or datetime.now()
        if (now - self._last_activity) >= self._timeout:
            self.logout(reason="SessionTimeout")
            return True
        return False

    def logout(self, reason: str = "UserLogout") -> None:
        """Beendet die aktive Sitzung am Terminal."""
        if self._current_user is None:
            return

        user_id = self._current_user.user_id
        self._state.release_session(user_id, self._terminal_id)
        self._state.log_audit("LOGOUT", user_id, f"Grund={reason}, Terminal={self._terminal_id}")
        self._current_user = None
        self._last_activity = None
