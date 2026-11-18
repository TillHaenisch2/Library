"""Tests für Vormerkungen, FIFO-Warteschlange, Stornierung (US-5) & Zustandsmodell."""

from __future__ import annotations

import pytest

from ssa_terminal.adapters.driven.mocks import SimulationContext
from ssa_terminal.application.auth_service import AuthService
from ssa_terminal.application.reserve_service import ReservationService
from ssa_terminal.domain.errors import (
    AlreadyBorrowedByUserError,
    AlreadyInQueueError,
    AlreadyReadyForPickupError,
    BookIsAvailableError,
    BookIsReferenceOnlyError,
    NotInQueueError,
    ReservationNotAllowedError,
)
from ssa_terminal.domain.models import BookState


def test_ac5_1_and_ac5_2_fifo_reservation_queue_order(
    auth_service: AuthService,
    reserve_service: ReservationService,
    ctx: SimulationContext,
) -> None:
    # B-13 ist an u-ben ausgeliehen, Warteschlange noch leer
    # AC 5.1: Erste Reservierung durch Anna -> Position 1
    auth_service.login_with_card("CARD-S1")
    event1 = reserve_service.reserve_book("B-13")
    assert event1.queue_position == 1
    assert ctx.books["B-13"].state == BookState.BORROWED
    assert ctx.books["B-13"].queue == ["u-anna"]

    # AC 5.2: Zweite Reservierung durch Clara -> Position 2 (FIFO)
    auth_service.login_with_card("CARD-S3")
    event2 = reserve_service.reserve_book("B-13")
    assert event2.queue_position == 2
    assert ctx.books["B-13"].queue == ["u-anna", "u-clara"]

    # Dritte Reservierung durch Professor -> Position 3
    auth_service.login_with_card("CARD-P1")
    event3 = reserve_service.reserve_book("B-13")
    assert event3.queue_position == 3
    assert ctx.books["B-13"].queue == ["u-anna", "u-clara", "u-prof"]

    # Benachrichtigungen wurden erzeugt (DSGVO: ohne Buchtitel!)
    assert len(ctx.notifications) == 3
    for msg in ctx.notifications:
        assert "Refactoring" not in msg


def test_ac5_3_duplicate_reservation_by_same_user_rejected(
    auth_service: AuthService,
    reserve_service: ReservationService,
    ctx: SimulationContext,
) -> None:
    # B-14 hat bereits u-ben in der Warteschlange
    auth_service.login_with_card("CARD-S2")
    with pytest.raises(AlreadyInQueueError) as exc:
        reserve_service.reserve_book("B-14")
    assert exc.value.code == "AlreadyInQueue"
    assert ctx.books["B-14"].queue == ["u-ben"]


def test_ac5_4_reserving_available_book_rejected(
    auth_service: AuthService,
    reserve_service: ReservationService,
) -> None:
    auth_service.login_with_card("CARD-S1")
    with pytest.raises(BookIsAvailableError) as exc:
        reserve_service.reserve_book("B-01")  # Available
    assert exc.value.code == "BookIsAvailable"


def test_ac5_5_reserving_reference_section_book_rejected(
    auth_service: AuthService,
    reserve_service: ReservationService,
) -> None:
    auth_service.login_with_card("CARD-S1")
    with pytest.raises(BookIsReferenceOnlyError) as exc:
        reserve_service.reserve_book("B-11")  # ReferenceSection
    assert exc.value.code == "BookIsReferenceOnly"


def test_ac5_6_reserving_own_ready_for_pickup_book_rejected(
    auth_service: AuthService,
    reserve_service: ReservationService,
) -> None:
    # B-17 liegt im Abholregal für Anna (u-anna)
    auth_service.login_with_card("CARD-S1")
    with pytest.raises(AlreadyReadyForPickupError) as exc:
        reserve_service.reserve_book("B-17")
    assert exc.value.code == "AlreadyReadyForPickup"


def test_other_user_can_queue_for_ready_for_pickup_book(
    auth_service: AuthService,
    reserve_service: ReservationService,
    ctx: SimulationContext,
) -> None:
    """Gemäß Zustandsmodell: interne Transition reservieren(u) während ReadyForPickup."""
    # B-17 liegt für Anna bereit; Ben darf sich in die Warteschlange einreihen
    auth_service.login_with_card("CARD-S2")
    event = reserve_service.reserve_book("B-17")
    assert event.queue_position == 1
    assert ctx.books["B-17"].state == BookState.READY_FOR_PICKUP
    assert ctx.books["B-17"].queue == ["u-ben"]


def test_ac5_7_self_reservation_by_current_borrower_rejected(
    auth_service: AuthService,
    reserve_service: ReservationService,
    ctx: SimulationContext,
) -> None:
    # B-13 ist aktuell an Ben (u-ben) ausgeliehen
    auth_service.login_with_card("CARD-S2")
    with pytest.raises(AlreadyBorrowedByUserError) as exc:
        reserve_service.reserve_book("B-13")
    assert exc.value.code == "AlreadyBorrowedByUser"
    assert ctx.books["B-13"].queue == []


def test_overdue_book_can_be_reserved_by_other_user_but_not_borrower(
    auth_service: AuthService,
    reserve_service: ReservationService,
    ctx: SimulationContext,
) -> None:
    """Gemäß Zustandsmodell gilt reservieren(u) in Overdue genauso wie in Borrowed."""
    ctx.books["B-13"].state = BookState.OVERDUE  # Ausleiher bleibt u-ben

    # Selbstreservierung durch Ben bleibt verboten
    auth_service.login_with_card("CARD-S2")
    with pytest.raises(AlreadyBorrowedByUserError):
        reserve_service.reserve_book("B-13")

    # Reservierung durch Anna erlaubt
    auth_service.login_with_card("CARD-S1")
    event = reserve_service.reserve_book("B-13")
    assert event.queue_position == 1
    assert ctx.books["B-13"].state == BookState.OVERDUE


def test_non_reservable_states_damaged_lost_in_processing(
    auth_service: AuthService,
    reserve_service: ReservationService,
    ctx: SimulationContext,
) -> None:
    auth_service.login_with_card("CARD-S1")
    for state in (BookState.IN_PROCESSING, BookState.DAMAGED, BookState.LOST):
        ctx.books["B-20"].state = state
        with pytest.raises(ReservationNotAllowedError):
            reserve_service.reserve_book("B-20")


def test_fr4_5_cancel_reservation_updates_fifo_queue(
    auth_service: AuthService,
    reserve_service: ReservationService,
    ctx: SimulationContext,
) -> None:
    # B-14 hat bereits u-ben auf Platz 1; u-clara reiht sich auf Platz 2 ein
    auth_service.login_with_card("CARD-S3")
    reserve_service.reserve_book("B-14")
    assert ctx.books["B-14"].queue == ["u-ben", "u-clara"]

    # Ben storniert seine Vormerkung -> Clara rückt automatisch auf Platz 1
    auth_service.login_with_card("CARD-S2")
    reserve_service.cancel_reservation("B-14")
    assert ctx.books["B-14"].queue == ["u-clara"]

    # Erneutes Stornieren durch Ben schlägt fehl
    with pytest.raises(NotInQueueError) as exc:
        reserve_service.cancel_reservation("B-14")
    assert exc.value.code == "NotInQueue"
