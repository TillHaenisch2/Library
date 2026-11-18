"""Tests für Ausleihe (UC-1, US-1 bis US-4), Grenzen, Alles-oder-Nichts & Atomarität."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from ssa_terminal.adapters.driven.mocks import (
    InMemoryLMSAdapter,
    SimulatedRFIDAdapter,
    SimulationContext,
)
from ssa_terminal.application.auth_service import AuthService
from ssa_terminal.application.checkout_service import CheckoutService
from ssa_terminal.domain.errors import (
    AlreadyBorrowedError,
    BookIsReferenceOnlyError,
    BookNotLoanableError,
    DomainError,
    MaxBooksLimitReachedError,
    MultipleBooksValidationError,
    ReservedForAnotherUserError,
)
from ssa_terminal.domain.models import BookState
from ssa_terminal.domain.rules import LoanPolicy, PolicyConfig


def test_checkout_without_login_fails(
    checkout_service: CheckoutService, rfid: SimulatedRFIDAdapter
) -> None:
    rfid.toggle_book("B-01")
    with pytest.raises(DomainError):
        checkout_service.checkout_scanned_books()


def test_ac1_1_student_successful_checkout_sets_28_days_and_disables_eas(
    auth_service: AuthService,
    checkout_service: CheckoutService,
    rfid: SimulatedRFIDAdapter,
    ctx: SimulationContext,
) -> None:
    today = date(2026, 11, 18)
    auth_service.login_with_card("CARD-S1")  # Anna hat 2/10 Büchern
    rfid.toggle_book("B-01")  # Available

    results = checkout_service.checkout_scanned_books(today=today)

    assert len(results) == 1
    assert results[0].book_id == "B-01"
    assert results[0].due_date == today + timedelta(days=28)

    # Kontingent & Buchzustand prüfen
    assert ctx.users_by_card["CARD-S1"].borrowed_count == 3
    book = ctx.books["B-01"]
    assert book.state == BookState.BORROWED
    assert book.borrower_id == "u-anna"
    assert book.due_date == today + timedelta(days=28)

    # FR-5.1: Diebstahlschutz auf Tag deaktiviert
    assert "B-01" in ctx.eas_disabled_books


def test_ac1_2_student_at_limit_10_cannot_borrow_more(
    auth_service: AuthService,
    checkout_service: CheckoutService,
    rfid: SimulatedRFIDAdapter,
    ctx: SimulationContext,
) -> None:
    auth_service.login_with_card("CARD-S3")  # Clara hat 10/10 Büchern
    rfid.toggle_book("B-01")

    with pytest.raises(MaxBooksLimitReachedError) as exc:
        checkout_service.checkout_scanned_books()
    assert exc.value.code == "MaxBooksLimitReached"

    # Zustand unverändert, EAS bleibt aktiv
    assert ctx.books["B-01"].state == BookState.AVAILABLE
    assert "B-01" not in ctx.eas_disabled_books
    assert ctx.users_by_card["CARD-S3"].borrowed_count == 10


def test_boundary_student_reaches_exact_limit_10_succeeds(
    auth_service: AuthService,
    checkout_service: CheckoutService,
    rfid: SimulatedRFIDAdapter,
    ctx: SimulationContext,
) -> None:
    auth_service.login_with_card("CARD-S2")  # Ben hat 8/10 Büchern
    rfid.toggle_book("B-01")
    rfid.toggle_book("B-02")

    results = checkout_service.checkout_scanned_books()
    assert len(results) == 2
    assert ctx.users_by_card["CARD-S2"].borrowed_count == 10
    assert {"B-01", "B-02"}.issubset(ctx.eas_disabled_books)


def test_ac1_3_batch_exceeding_limit_aborts_completely_all_or_nothing(
    auth_service: AuthService,
    checkout_service: CheckoutService,
    rfid: SimulatedRFIDAdapter,
    ctx: SimulationContext,
) -> None:
    auth_service.login_with_card("CARD-S2")  # Ben hat 8/10 Büchern
    rfid.toggle_book("B-01")
    rfid.toggle_book("B-02")
    rfid.toggle_book("B-03")  # 8 + 3 = 11 -> Überschreitung beim 3. Buch

    with pytest.raises(MaxBooksLimitReachedError):
        checkout_service.checkout_scanned_books()

    # Alles-oder-Nichts: KEINES der 3 Bücher darf gebucht oder entsichert sein!
    for bid in ("B-01", "B-02", "B-03"):
        assert ctx.books[bid].state == BookState.AVAILABLE
        assert ctx.books[bid].borrower_id is None
        assert bid not in ctx.eas_disabled_books
    assert ctx.users_by_card["CARD-S2"].borrowed_count == 8


def test_nfr_p2_max_5_books_per_scan_boundary(
    auth_service: AuthService,
    checkout_service: CheckoutService,
    rfid: SimulatedRFIDAdapter,
    ctx: SimulationContext,
) -> None:
    auth_service.login_with_card("CARD-P1")  # Professor (kein Limit)

    # 5 Bücher gleichzeitig -> erlaubt
    for bid in ("B-01", "B-02", "B-03", "B-04", "B-05"):
        rfid.toggle_book(bid)
    results = checkout_service.checkout_scanned_books()
    assert len(results) == 5

    # 6 Bücher gleichzeitig -> abgelehnt
    rfid.clear_scanned_books()
    for bid in ("B-06", "B-07", "B-08", "B-09", "B-10", "B-13"):
        rfid.toggle_book(bid)
    with pytest.raises(DomainError):
        checkout_service.checkout_scanned_books()
    assert "B-06" not in ctx.eas_disabled_books


def test_ac2_1_and_ac2_2_professor_no_limit_no_due_date_and_rejects_borrowed(
    auth_service: AuthService,
    checkout_service: CheckoutService,
    rfid: SimulatedRFIDAdapter,
    ctx: SimulationContext,
) -> None:
    auth_service.login_with_card("CARD-P1")  # Prof hat bereits 14 Bücher

    # AC 2.1: Ausleihe ohne Frist
    rfid.toggle_book("B-01")
    results = checkout_service.checkout_scanned_books()
    assert results[0].due_date is None
    assert ctx.books["B-01"].due_date is None
    assert ctx.books["B-01"].state == BookState.BORROWED

    # AC 2.2: Bereits ausgeliehenes Buch ablehnen
    rfid.clear_scanned_books()
    rfid.toggle_book("B-13")  # Borrowed by u-ben
    with pytest.raises(AlreadyBorrowedError) as exc:
        checkout_service.checkout_scanned_books()
    assert exc.value.code == "AlreadyBorrowed"
    assert "B-13" not in ctx.eas_disabled_books


def test_ac3_1_reference_section_blocked_for_student_and_professor(
    auth_service: AuthService,
    checkout_service: CheckoutService,
    rfid: SimulatedRFIDAdapter,
    ctx: SimulationContext,
) -> None:
    for card_id in ("CARD-S1", "CARD-P1"):
        auth_service.login_with_card(card_id)
        rfid.clear_scanned_books()
        rfid.toggle_book("B-11")  # ReferenceSection

        with pytest.raises(BookIsReferenceOnlyError) as exc:
            checkout_service.checkout_scanned_books()
        assert exc.value.code == "BookIsReferenceOnly"
        assert ctx.books["B-11"].state == BookState.REFERENCE_SECTION
        assert "B-11" not in ctx.eas_disabled_books


def test_ac4_1_and_ac4_2_ready_for_pickup_only_for_holder_and_keeps_queue(
    auth_service: AuthService,
    checkout_service: CheckoutService,
    rfid: SimulatedRFIDAdapter,
    ctx: SimulationContext,
) -> None:
    # B-19 liegt im Abholregal für u-ben, u-clara steht in der Warteschlange
    # AC 4.2: Unberechtigter Abholer (Anna) wird blockiert
    auth_service.login_with_card("CARD-S1")
    rfid.toggle_book("B-19")
    with pytest.raises(ReservedForAnotherUserError) as exc:
        checkout_service.checkout_scanned_books()
    assert exc.value.code == "ReservedForAnotherUser"
    assert ctx.books["B-19"].state == BookState.READY_FOR_PICKUP

    # AC 4.1: Berechtigter Abholer (Ben) darf ausleihen; Warteschlange bleibt erhalten (FR-4.4)
    auth_service.login_with_card("CARD-S2")
    results = checkout_service.checkout_scanned_books()
    assert len(results) == 1
    assert ctx.books["B-19"].state == BookState.BORROWED
    assert ctx.books["B-19"].borrower_id == "u-ben"
    assert ctx.books["B-19"].holder_id is None
    assert ctx.books["B-19"].queue == ["u-clara"]
    assert "B-19" in ctx.eas_disabled_books


def test_uc1_extension_1b_multiple_invalid_books_in_batch_rollback_completely(
    auth_service: AuthService,
    checkout_service: CheckoutService,
    rfid: SimulatedRFIDAdapter,
    ctx: SimulationContext,
) -> None:
    """Kombination aus gültigem Buch (B-01) und zwei ungültigen (B-11, B-19)."""
    auth_service.login_with_card("CARD-S1")  # Anna (2/10 -> 2 + 3 = 5 <= 10, Limit wird nicht gerissen)
    rfid.toggle_book("B-01")  # gültig (Available)
    rfid.toggle_book("B-11")  # ungültig (ReferenceSection)
    rfid.toggle_book("B-19")  # ungültig (ReadyForPickup für Ben)

    with pytest.raises(MultipleBooksValidationError) as exc:
        checkout_service.checkout_scanned_books()

    error_codes = {e.book_id: e.code for e in exc.value.errors}
    assert error_codes == {
        "B-11": "BookIsReferenceOnly",
        "B-19": "ReservedForAnotherUser",
    }

    # Auch das gültige Buch B-01 darf NICHT ausgeliehen oder entsichert sein
    assert ctx.books["B-01"].state == BookState.AVAILABLE
    assert "B-01" not in ctx.eas_disabled_books
    assert ctx.users_by_card["CARD-S1"].borrowed_count == 2

def test_in_processing_book_cannot_be_borrowed(
    auth_service: AuthService,
    checkout_service: CheckoutService,
    rfid: SimulatedRFIDAdapter,
) -> None:
    auth_service.login_with_card("CARD-S1")
    rfid.toggle_book("B-20")  # InProcessing
    with pytest.raises(BookNotLoanableError):
        checkout_service.checkout_scanned_books()


def test_nfr_r1_atomicity_no_eas_disable_if_lms_save_fails(
    auth_service: AuthService,
    rfid: SimulatedRFIDAdapter,
    lms: InMemoryLMSAdapter,
    state,
    ctx: SimulationContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Wenn LMS beim Buchen abbricht (NFR-R3), darf EAS nicht deaktiviert werden."""
    service = CheckoutService(auth_service, rfid, lms, state)
    auth_service.login_with_card("CARD-S1")
    rfid.toggle_book("B-01")

    def broken_save(_books) -> None:
        raise RuntimeError("LMS connection lost")

    monkeypatch.setattr(lms, "save_books", broken_save)

    with pytest.raises(RuntimeError, match="LMS connection lost"):
        service.checkout_scanned_books()

    assert "B-01" not in ctx.eas_disabled_books


def test_nfr_m1_configurable_policy_parameters(
    auth_service: AuthService,
    rfid: SimulatedRFIDAdapter,
    lms: InMemoryLMSAdapter,
    state,
    ctx: SimulationContext,
) -> None:
    """Geschäftsparameter (Limit & Leihfrist) wirken ohne Codeänderung."""
    custom_policy = LoanPolicy(PolicyConfig(student_max_books=3, student_loan_days=14))
    service = CheckoutService(auth_service, rfid, lms, state, policy=custom_policy)

    today = date(2026, 11, 18)
    auth_service.login_with_card("CARD-S1")  # Anna hat 2 Bücher
    rfid.toggle_book("B-01")
    results = service.checkout_scanned_books(today=today)
    assert results[0].due_date == today + timedelta(days=14)

    # 4. Buch schlägt bei Limit=3 fehl
    rfid.clear_scanned_books()
    rfid.toggle_book("B-02")
    with pytest.raises(MaxBooksLimitReachedError):
        service.checkout_scanned_books(today=today)
