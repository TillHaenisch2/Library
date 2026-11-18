"""Tests für Identifikation, Sitzungssperre (US-6) und 30s-Timeout (NFR-S1)."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from ssa_terminal.adapters.driven.mocks import SimulationContext
from ssa_terminal.application.auth_service import AuthService
from ssa_terminal.domain.errors import AlreadyLoggedInElsewhereError, UserNotFoundError
from ssa_terminal.domain.models import UserRole


def test_fr1_1_login_resolves_student_and_professor(
    auth_service: AuthService,
) -> None:
    student = auth_service.login_with_card("CARD-S1")
    assert student.user_id == "u-anna"
    assert student.role == UserRole.STUDENT
    assert student.borrowed_count == 2

    prof = auth_service.login_with_card("CARD-P1")
    assert prof.user_id == "u-prof"
    assert prof.role == UserRole.PROFESSOR


def test_login_unknown_card_raises_user_not_found(
    auth_service: AuthService, ctx: SimulationContext
) -> None:
    with pytest.raises(UserNotFoundError) as exc:
        auth_service.login_with_card("CARD-UNKNOWN")
    assert exc.value.code == "UserNotFound"
    assert auth_service.current_user is None
    assert ctx.audit_log[-1].event_type == "LOGIN_FAILED"


def test_ac6_1_second_terminal_login_rejected_while_session_active(
    auth_service: AuthService,
    second_terminal_auth: AuthService,
) -> None:
    # Student Anna meldet sich an Terminal 1 an
    user_t1 = auth_service.login_with_card("CARD-S1")
    assert user_t1.user_id == "u-anna"

    # Zweite Anmeldung an Terminal 2 muss fehlschlagen
    with pytest.raises(AlreadyLoggedInElsewhereError) as exc:
        second_terminal_auth.login_with_card("CARD-S1")
    assert exc.value.code == "AlreadyLoggedInElsewhere"
    assert second_terminal_auth.current_user is None

    # Sitzung an Terminal 1 bleibt unverändert aktiv
    assert auth_service.current_user is not None
    assert auth_service.current_user.user_id == "u-anna"


def test_ac6_2_second_terminal_login_succeeds_after_logout(
    auth_service: AuthService,
    second_terminal_auth: AuthService,
) -> None:
    auth_service.login_with_card("CARD-S1")
    auth_service.logout()

    user_t2 = second_terminal_auth.login_with_card("CARD-S1")
    assert user_t2.user_id == "u-anna"


def test_nfr_s1_session_timeout_boundary_29s_vs_30s(
    auth_service: AuthService,
    second_terminal_auth: AuthService,
) -> None:
    t0 = datetime(2026, 11, 18, 10, 0, 0)
    auth_service.login_with_card("CARD-S1", now=t0)

    # Nach 29 Sekunden: Sitzung muss noch aktiv sein
    assert auth_service.check_timeout(now=t0 + timedelta(seconds=29)) is False
    assert auth_service.current_user is not None

    # Nach exakt 30 Sekunden: automatische Abmeldung und Freigabe für Terminal 2
    assert auth_service.check_timeout(now=t0 + timedelta(seconds=30)) is True
    assert auth_service.current_user is None

    user_t2 = second_terminal_auth.login_with_card("CARD-S1", now=t0 + timedelta(seconds=31))
    assert user_t2.user_id == "u-anna"


def test_touch_extends_session_timeout(auth_service: AuthService) -> None:
    t0 = datetime(2026, 11, 18, 10, 0, 0)
    auth_service.login_with_card("CARD-S1", now=t0)

    # Aktion nach 20s setzt Timer zurück
    auth_service.touch(now=t0 + timedelta(seconds=20))

    # 45s nach Login (aber erst 25s nach letzter Aktion) noch aktiv
    assert auth_service.check_timeout(now=t0 + timedelta(seconds=45)) is False
    assert auth_service.current_user is not None

    # 50s nach Login (30s nach letzter Aktion) beendet
    assert auth_service.check_timeout(now=t0 + timedelta(seconds=50)) is True
    assert auth_service.current_user is None
