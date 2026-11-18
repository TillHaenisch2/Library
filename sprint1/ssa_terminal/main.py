"""Composition Root für das Self-Service-Ausleihe Walking Skeleton (Sprint 1)."""

from __future__ import annotations

import tkinter as tk

from ssa_terminal.adapters.driven.mocks import (
    ConsoleNotificationAdapter,
    InMemoryIdMAdapter,
    InMemoryLMSAdapter,
    InMemoryStateAdapter,
    SimulatedRFIDAdapter,
    SimulationContext,
)
from ssa_terminal.adapters.driving.tkinter_app import SSATerminalApp
from ssa_terminal.application.auth_service import AuthService
from ssa_terminal.application.checkout_service import CheckoutService
from ssa_terminal.application.reserve_service import ReservationService


def main() -> None:
    ctx = SimulationContext()

    rfid_adapter = SimulatedRFIDAdapter(ctx)
    lms_adapter = InMemoryLMSAdapter(ctx)
    idm_adapter = InMemoryIdMAdapter(ctx)
    state_adapter = InMemoryStateAdapter(ctx)
    notify_adapter = ConsoleNotificationAdapter(ctx)

    auth_service = AuthService(
        idm_port=idm_adapter,
        lms_port=lms_adapter,
        state_port=state_adapter,
        terminal_id="TERM-01",
        session_timeout_seconds=30,
    )
    checkout_service = CheckoutService(
        auth_service=auth_service,
        rfid_port=rfid_adapter,
        lms_port=lms_adapter,
        state_port=state_adapter,
    )
    reserve_service = ReservationService(
        auth_service=auth_service,
        lms_port=lms_adapter,
        state_port=state_adapter,
        notification_port=notify_adapter,
    )

    root = tk.Tk()
    SSATerminalApp(
        root=root,
        ctx=ctx,
        rfid_adapter=rfid_adapter,
        auth_service=auth_service,
        checkout_service=checkout_service,
        reserve_service=reserve_service,
    )
    root.mainloop()


if __name__ == "__main__":
    main()
