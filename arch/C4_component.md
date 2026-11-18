flowchart TB
    classDef person fill:#08427B,stroke:#052E56,color:#FFFFFF
    classDef driving fill:#438DD5,stroke:#2E6295,color:#FFFFFF
    classDef app fill:#1168BD,stroke:#0B4884,color:#FFFFFF
    classDef domain fill:#0B4884,stroke:#052E56,color:#FFFFFF
    classDef port fill:#85BBF0,stroke:#2E6295,color:#052E56
    classDef driven fill:#6C9AC3,stroke:#2E6295,color:#FFFFFF

    User["<b>Benutzer / Tester</b><br/>[Person]<br/>Student, Professor oder<br/>Bibliothekar im Testbetrieb"]:::person

    subgraph Modulith ["Terminal-Applikation (Modulith) [Python / tkinter]"]
        subgraph Driving ["Driving Adapters (UI & Simulator)"]
            Harness["<b>Test-Harness Panel</b><br/>[tkinter Frame: Links & Mitte]<br/>Studi/Prof-Buttons, Buch-Toggles,<br/>Abmelden- & Reset-Trigger"]:::driving
            TerminalUI["<b>Terminal-Screen UI</b><br/>[tkinter Frame: Unten]<br/>Schwarzes Ausgabefenster, Ausleih-Button,<br/>DSGVO-gefilterte Anzeige (NFR-D2)"]:::driving
        end

        subgraph Core ["Application & Domain Core (Clean Architecture)"]
            UseCases["<b>Application Services / Use Cases</b><br/>[Python Package: application]<br/>LoginService, CheckoutService (UC-1),<br/>ReservationService (US-5), SessionTimeout"]:::app
            Domain["<b>Domain Model & Rules</b><br/>[Python Package: domain]<br/>Book (State Machine), User & Role,<br/>LoanPolicy (Frist & Limit), Alles-oder-Nichts"]:::domain
        end

        subgraph Ports ["Driven Ports (Interfaces / Protocols)"]
            RFIDPort["<b>RFIDReaderPort</b><br/>[typing.Protocol]<br/>get_scanned_books(), disable_eas(book_ids)"]:::port
            LMSPort["<b>LMSPort</b><br/>[typing.Protocol]<br/>get_book(), checkout_books(), reserve()"]:::port
            IdMPort["<b>IdMPort</b><br/>[typing.Protocol]<br/>resolve_user(card_id)"]:::port
            StatePort["<b>LocalStatePort</b><br/>[typing.Protocol]<br/>Session-Lock, Queue-State & Audit-Log"]:::port
            NotifyPort["<b>NotificationPort</b><br/>[typing.Protocol]<br/>notify_pickup_ready(user_id)"]:::port
        end

        subgraph Driven ["Driven Adapters (Sprint 1: In-Process Mocks)"]
            MockRFID["<b>SimulatedRFIDAdapter</b><br/>Liest Toggle-Zustand aus Harness &<br/>protokolliert EAS-Deaktivierung"]:::driven
            MockLMS["<b>InMemoryLMSAdapter</b><br/>Dict mit ca. 20 Testbüchern &<br/>Ausleihkonten (inkl. Reset)"]:::driven
            MockIdM["<b>InMemoryIdMAdapter</b><br/>Dict mit Test-Studis & Prof"]:::driven
            MockState["<b>InMemoryStateAdapter</b><br/>Lokale Session-, Warteschlangen- &<br/>Audit-Speicherung"]:::driven
            MockNotify["<b>ConsoleNotificationAdapter</b><br/>Schreibt Benachrichtigungs-Events<br/>ins Log / Output"]:::driven
        end
    end

    User -->|"Klickt Toggles, Abmelden, Reset"| Harness
    User -->|"Klickt Ausleihe & liest Output"| TerminalUI

    Harness -->|"Setzt aufgelegte Bücher /<br/>triggert Scan- & Reset-Events"| MockRFID
    Harness -->|"Meldet Karte an / ab"| UseCases
    TerminalUI -->|"Startet Ausleihe / Vormerkung &<br/>rendert Ergebnis"| UseCases

    UseCases -->|"Prüft Regeln &<br/>führt Zustandsübergänge aus"| Domain
    UseCases --> RFIDPort
    UseCases --> LMSPort
    UseCases --> IdMPort
    UseCases --> StatePort
    UseCases --> NotifyPort

    MockRFID -.->|implementiert| RFIDPort
    MockLMS -.->|implementiert| LMSPort
    MockIdM -.->|implementiert| IdMPort
    MockState -.->|implementiert| StatePort
    MockNotify -.->|implementiert| NotifyPort