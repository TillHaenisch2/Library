"""Gemeinsame Pytest-Fixtures für die Regressionstest-Suite."""

from __future__ import annotations

import pytest

from ssa_terminal.adapters.driven.mocks import (
    ConsoleNotificationAdapter,
    InMemoryIdMAdapter,
    InMemoryLMSAdapter,
    InMemoryStateAdapter,
    SimulatedRFIDAdapter,
    SimulationContext,
)
from ssa_terminal.application.auth_service import AuthService
from ssa_terminal.application.checkout_service import CheckoutService
from ssa_terminal.application.reserve_service import ReservationService
from ssa_terminal.domain.rules import LoanPolicy, PolicyConfig


@pytest.fixture
def ctx() -> SimulationContext:
    """Frischer, deterministischer Simulationszustand pro Test."""
    return SimulationContext()


@pytest.fixture
def rfid(ctx: SimulationContext) -> SimulatedRFIDAdapter:
    return SimulatedRFIDAdapter(ctx)


@pytest.fixture
def lms(ctx: SimulationContext) -> InMemoryLMSAdapter:
    return InMemoryLMSAdapter(ctx)


@pytest.fixture
def idm(ctx: SimulationContext) -> InMemoryIdMAdapter:
    return InMemoryIdMAdapter(ctx)


@pytest.fixture
def state(ctx: SimulationContext) -> InMemoryStateAdapter:
    return InMemoryStateAdapter(ctx)


@pytest.fixture
def notify(ctx: SimulationContext) -> ConsoleNotificationAdapter:
    return ConsoleNotificationAdapter(ctx)


@pytest.fixture
def auth_service(
    idm: InMemoryIdMAdapter,
    lms: InMemoryLMSAdapter,
    state: InMemoryStateAdapter,
) -> AuthService:
    return AuthService(
        idm_port=idm,
        lms_port=lms,
        state_port=state,
        terminal_id="TERM-01",
        session_timeout_seconds=30,
    )


@pytest.fixture
def second_terminal_auth(
    idm: InMemoryIdMAdapter,
    lms: InMemoryLMSAdapter,
    state: InMemoryStateAdapter,
) -> AuthService:
    """Zweites Terminal zur Prüfung von US-6 (Single-Session-Lock)."""
    return AuthService(
        idm_port=idm,
        lms_port=lms,
        state_port=state,
        terminal_id="TERM-02",
        session_timeout_seconds=30,
    )


@pytest.fixture
def checkout_service(
    auth_service: AuthService,
    rfid: SimulatedRFIDAdapter,
    lms: InMemoryLMSAdapter,
    state: InMemoryStateAdapter,
) -> CheckoutService:
    return CheckoutService(
        auth_service=auth_service,
        rfid_port=rfid,
        lms_port=lms,
        state_port=state,
        policy=LoanPolicy(PolicyConfig()),
    )


@pytest.fixture
def reserve_service(
    auth_service: AuthService,
    lms: InMemoryLMSAdapter,
    state: InMemoryStateAdapter,
    notify: ConsoleNotificationAdapter,
) -> ReservationService:
    return ReservationService(
        auth_service=auth_service,
        lms_port=lms,
        state_port=state,
        notification_port=notify,
    )
