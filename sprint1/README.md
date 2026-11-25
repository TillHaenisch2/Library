Dsa Layout ist:


- **ssa_terminal/**
  - **domain/** – Keine externen Abhängigkeiten (reines Python)
    - `models.py` – Book, BookState, User, UserRole, Loan, Reservation
    - `rules.py` – Fristberechnung (28d vs. None), Limitprüfung (max 10), Alles-oder-Nichts
    - `errors.py` – MaxBooksLimitReached, BookIsReferenceOnly, ReservedForAnotherUser, ...
  - **application/** – Orchestriert Domain + Ports
    - `ports.py` – Interfaces (typing.Protocol) für RFID, LMS, IdM, State, Notification
    - `auth_service.py` – Anmeldung, Single-Session-Check (US-6), 30s-Timeout, Abmelden
    - `checkout_service.py` – UC-1 (Einzel- & Mehrfachausleihe, atomares Buchen + EAS)
    - `reserve_service.py` – US-5 (FIFO-Warteschlange, Stornierung, AC 5.1–5.7)
  - **adapters/**
    - **driving/**
      - `tkinter_app.py` – Links: User/Reset, Mitte: Buch-Toggles, Unten: Terminal-Output
    - **driven/**
      - `mocks.py` – In-Memory Dicts (~20 Bücher, Studis, Prof) + Reset-Funktion
  - **tests/** – Automatisierte Unit- & Akzeptanztests gegen UseCases (für Sprint 2)
  - `main.py` – Composition Root (verdrahtet Mocks -> UseCases -> tkinter_app)

