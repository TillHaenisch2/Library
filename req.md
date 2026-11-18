
# Bibliothek: self-service Ausleihe


---

## 1. Systemübersicht & Akteure

Das System verarbeitet Ausleihvorgänge an einem Self-Service-Terminal über RFID-Reader. 

### Akteure

* **Student:** Standard-Benutzer mit Ausleihbeschränkungen.
* **Professor:** Privilegierter Benutzer mit Sonderrechten.
* **Bibliothekar:** Verwalter für Sonderfälle und Bereitstellung (Infrastruktur-Akteur).

* **Benutzer** ist entweder Student oder Professor. Spätere Erweiterung auf z.B. Mitarbeiter, Gast
---

## 2. Functional Requirements (FR)

### FR-1: Identifikation & Berechtigungen

* **FR-1.1:** Das System muss Benutzer anhand ihrer Karten-ID identifizieren und deren Rolle (`Student`, `Professor`) auflösen.
* **FR-1.2:** Das System muss für Studenten das aktuelle Ausleihkontingent (bereits geliehene Bücher) prüfen. Ein Student darf maximal **10 Bücher** gleichzeitig ausgeliehen haben.
* **FR-1.3:** Professoren haben **kein Limit** bezüglich der Anzahl ausleihbarer Bücher.

### FR-2: Buchzustände & Ausleihregeln

* **FR-2.1:** Ein Buch im regulären Bestand (`NormalShelf`) darf von jedem berechtigten Benutzer ausgeliehen werden.
* **FR-2.2:** Ein Buch im Präsenzbestand / Handapparat (`ReferenceSection`) darf **niemals** ausgeliehen werden.
* **FR-2.3:** Ein bereits ausgeliehenes Buch (`Borrowed`) kann nicht erneut ausgeliehen werden.
* **FR-2.4:** Ein reserviertes Buch im Abholregal (`ReadyForPickup`) kann **nur** von der Person ausgeliehen werden, für die es reserviert wurde.


### FR-3: Leihfristen und Limits

* **FR-3.1:** Für Studenten beträgt die Leihfrist **28 Kalendertage** ab Ausleihdatum.
* **FR-3.2:** Für Professoren gibt es **keine Leihfrist** (`DueDate = None` / unbegrenzt).
* **FR-3.3:** Würde bei einer Mehrfachausleihe das Limit überschritten, wird die Ausleihe nicht durchgeführt.

### FR-4: Reservierung & Warteschlange

* **FR-4.1:** Nicht verfügbare (bereits ausgeliehene) Bücher können von Benutzern reserviert werden. Die Warteschlange ist Teil des Buchzustands; eine Reservierung ändert den Zustand des Buchs nicht.
* **FR-4.2:** Reservierungen bilden eine strikte Warteschlange nach dem FIFO-Prinzip.
* **FR-4.3:** Wird ein reserviertes Buch zurückgegeben, wandert es in das Abholregal (`ReadyForPickup`) und der nächste Benutzer in der Warteschlange erhält eine automatische Benachrichtigung.
* **FR-4.4:** Leiht der berechtigte Benutzer ein Buch im Zustand `ReadyForPickup` aus, geht es in `Borrowed` über; die verbleibende Warteschlange bleibt erhalten.
* **FR-4.5:** Eine Reservierung kann jederzeit storniert werden.

### FR-5: Diebstahlschutz

* **FR-5.1:** Bei erfolgreicher Ausleihe muss das System den Diebstahlschutz des RFID-Tags des ausgeliehenen Buchs deaktivieren (vgl. UC-1, Postcondition 3).

---

## 3. Non-Functional Requirements (NFR)

### Performance / Zeitverhalten

* **NFR-P1:** Zwischen dem Auflegen eines Buchs und der Anzeige des Ergebnisses (Erfolg oder Fehler) vergehen in 95% der Fälle höchstens **2 s**, maximal höchstens **5 s**.
* **NFR-P2:** Der RFID-Reader erfasst bis zu **5 gleichzeitig aufgelegte Bücher** in einem Vorgang .
  

### Zuverlässigkeit & Konsistenz

* **NFR-R1 (Atomarität):** Die Buchung auf das Benutzerkonto und die Deaktivierung des Diebstahlschutzes erfolgen atomar. Ein Buch ist nie entsichert, ohne gebucht zu sein, und nie gebucht, ohne entsichert zu sein (vgl. FR-5.1).
* **NFR-R2 (Nebenläufigkeit):** Auch bei gleichzeitigen Vorgängen an mehreren Terminals wird ein Buch nie doppelt verliehen, und das Limit von 10 Büchern pro Student wird nie überschritten. Fachlich abgesichert durch US-6 (nur eine Sitzung pro Benutzer).
* **NFR-R3 (Verhalten bei Verbindungsausfall):** Ist das Bibliotheksmanagementsystem nicht erreichbar, verweigert das Terminal die Ausleihe mit einem verständlichen Hinweis. (u.a. um Überschreitung des Limits und andere Inkonsistenzen zu verhindern)

### Security

* **NFR-S1 (Session-Ende):** Eine Sitzung am Terminal endet nach **30 s** ohne Aktion. Alternative/Ergänzung: Automatische Abmeldung nach Ausleihvorgang ?
* **NFR-S2:** Der Diebstahlschutz eines Tags kann nur durch ein authentisiertes Terminal deaktiviert werden, nicht durch beliebige RFID-Reader.
* **NFR-S3 (Audit):** Alle Ausleih-, Rückgabe- und Fehlvorgänge werden manipulationssicher protokolliert.
* **NFR-S4:** Die Kommunikation zwischen Terminal und Backend ist verschlüsselt und gegenseitig authentisiert.

### Datenschutz (DSGVO)

* **NFR-D1 (Datensparsamkeit):** Die Verknüpfung zwischen Benutzer und Buch wird unmittelbar nach der Rückgabe gelöscht, sofern keine offenen Gebühren bestehen. Leihhistorien werden nicht gespeichert. 
* **NFR-D2:** Das Display zeigt keine vollständigen Kontodaten und keine Titel weiterer ausgeliehener Bücher an (Schutz vor Shoulder-Surfing).
* **NFR-D3:** Benachrichtigungen (FR-4.3) über unverschlüsselte Kanäle enthalten keinen Buchtitel.

### Usability & Barrierefreiheit

* **NFR-U1:** Ein Erstbenutzer kann ohne Hilfe in unter **60 s** ein Buch ausleihen (nachgewiesen durch Usability-Test, 95% reichen).
* **NFR-U2:** Das Terminal ist barrierefrei bedienbar (u. a. rollstuhlgerechte Höhe, Kontrast, Schriftgröße, akustisches Feedback) nach ISO ...
* **NFR-U3:** Die Benutzeroberfläche ist auf Deutsch und Englisch verfügbar.
* **NFR-U4:** Jede Fehlermeldung nennt den Grund und den nächsten Schritt für den Benutzer.

### Wartbarkeit & Interoperabilität

* **NFR-M1:** Geschäftsparameter (Ausleihlimit, Leihfrist, Abholfrist) sind ohne Code-Änderung konfigurierbar.
* **NFR-M2:** Neue Benutzerrollen (z. B. Mitarbeiter, externe Nutzer) lassen sich ohne Änderung der Ausleihlogik ergänzen.
* **NFR-I1:** Das Terminal kommuniziert mit dem Bibliotheksmanagementsystem über Standard-Protokolle (SIP2, klären).
* **NFR-I2:** Die Datenstruktur der RFID-Tags entspricht ISO ....

---

## 4. User Stories


Epic 1: Self-Service Ausleihe am RFID-Terminal

US-1: **Buch ausleihen** (Student)
Als Student
möchte ich meine ausgewählten Bücher am RFID-Reader scannen,
um sie auf mein Bibliothekskonto auszuleihen,
soweit ich mein Limit von 10 Büchern nicht überschreite.

### Akzeptanzkriterien (Acceptance Criteria):
* **AC 1.1 (Erfolgreiche Ausleihe)**: 
  * **Angenommen** der Student hat aktuell 2 Bücher ausgeliehen und das gescannte Buch ist im regulären Regal (`NormalShelf`) verfügbar.
  * **Wenn** der Student das Buch ausleiht.
  * **Dann** ist der Vorgang erfolgreich, die neue Ausleihzahl des Studenten ist 3, der Buchzustand ist `Borrowed` und das Fälligkeitsdatum liegt 28 Kalendertage in der Zukunft.
* **AC 1.2 (Limit erreicht):**
  * **Angenommen** der Student hat bereits 10 Bücher ausgeliehen.
  * **Wenn** der Student versucht, ein weiteres verfügbares Buch auszuleihen.
  * **Dann** schlägt der Vorgang fehl mit dem Fehler "Maximales Limit erreicht" (`MaxBooksLimitReached`) und der Buchzustand ändert sich nicht.
* **AC 1.3 (Limit wird bei Mehrfachausleihe überschritten):**
  * **Angenommen** der Student hat bereits 8 Bücher ausgeliehen.
  * **Wenn** der Student versucht, 3 weitere verfügbare Bücher auszuleihen.
  * **Dann** schlägt der Vorgang fehl mit dem Fehler "Maximales Limit erreicht" (`MaxBooksLimitReached`) und  der Meldung "Bitte Bücher entfernen" und der Buchzustand ändert sich nicht.

---

US-2: **Buch ausleihen** (Professor)
Als Professor
möchte ich Bücher ohne Begrenzung der Anzahl und ohne Fälligkeitsdatum ausleihen,
um meine Lehr- und Forschungsarbeit flexibel zu unterstützen.

**Akzeptanzkriterien:**
* **AC 2.1 (Erfolgreich ohne Frist):**
  * **Angenommen** der Benutzer ist ein Professor und das Buch ist verfügbar.
  * **Wenn** der Professor das Buch ausleiht.
  * **Dann** ist der Vorgang erfolgreich, der Buchzustand ist `Borrowed` und es gibt **kein** Fälligkeitsdatum (`DueDate = None`).
* **AC 2.2 (Bereits ausgeliehen):**
  * **Angenommen** das Buch ist bereits an jemand anderen ausgeliehen (`Borrowed`).
  * **Wenn** der Professor versucht, das Buch am Terminal auszuleihen.
  * **Dann** schlägt der Vorgang fehl mit dem Fehler "Bereits ausgeliehen" (`AlreadyBorrowed`).

---

US-3: **Schutz des Handapparats**
Als Bibliothekar
möchte ich, dass Präsenzbestände (Handapparat) am Terminal automatisch abgelehnt werden,
damit sie den Lesesaal nicht verlassen.

**Akzeptanzkriterien:**
* **AC 3.1 (Präsenzbestand blockieren):**
  * **Angenommen** ein Buch gehört zum Präsenzbestand (`ReferenceSection`).
  * **Wenn** ein beliebiger Benutzer (Student oder Professor) versucht, es auszuleihen.
  * **Dann** schlägt der Vorgang fehl mit dem Fehler "Nur Präsenzbestand" (`BookIsReferenceOnly`).

---

US-4: **Reserviertes Buch abholen**
Als Benutzer (Student oder Professor)
möchte ich ein für mich im Abholregal bereitgestelltes Buch scannen und ausleihen können,
wobei andere Benutzer am Terminal blockiert werden, falls sie versuchen, mein reserviertes Buch mitzunehmen.

**Akzeptanzkriterien:**
* **AC 4.1 (Berechtigter Abholer):**
  * **Angenommen** ein Buch liegt im Abholregal (`ReadyForPickup`) für Student A.
  * **Wenn** Student A das Buch am Terminal ausleiht.
  * **Dann** ist der Vorgang erfolgreich und das Buch geht in den Zustand `Borrowed` für Student A über.
* **AC 4.2 (Unberechtigter Abholer):**
  * **Angenommen** ein Buch liegt im Abholregal (`ReadyForPickup`) für Student A.
  * **Wenn** Professor B (oder Student C) versucht, das Buch auszuleihen.
  * **Dann** schlägt der Vorgang fehl mit dem Fehler "Für anderen Benutzer reserviert" (`ReservedForAnotherUser`).

---

US-6: **Nur eine Sitzung pro Benutzer**
Als Bibliothekar
möchte ich, dass ein Benutzer nur an einem Terminal gleichzeitig angemeldet sein kann,
damit das Ausleihlimit nicht durch parallele Ausleihen an mehreren Terminals umgangen wird (vgl. NFR-R2).

**Akzeptanzkriterien:**
* **AC 6.1 (Zweite Anmeldung ablehnen):**
  * **Angenommen** Student A ist an Terminal 1 angemeldet.
  * **Wenn** Student A seinen Ausweis an Terminal 2 auflegt.
  * **Dann** schlägt die Anmeldung an Terminal 2 fehl mit dem Fehler "Bereits an anderem Terminal angemeldet" (`AlreadyLoggedInElsewhere`) und die Sitzung an Terminal 1 bleibt unverändert.
* **AC 6.2 (Anmeldung nach Sitzungsende):**
  * **Angenommen** Student A war an Terminal 1 angemeldet und die Sitzung ist beendet (Abmeldung oder Timeout nach NFR-S1).
  * **Wenn** Student A seinen Ausweis an Terminal 2 auflegt.
  * **Dann** ist die Anmeldung an Terminal 2 erfolgreich.

---

Epic 2: Vorestellung/Reservierung

US-5: **Vorbestellung / Warteschlange**
Als Benutzer
möchte ich ein zurzeit ausgeliehenes Buch reservieren können,
damit ich automatisch benachrichtigt werde, sobald es für mich im Abholregal bereitsteht.

**Akzeptanzkriterien (Acceptance Criteria):**

* **AC 5.1 (Erste Reservierung eines ausgeliehenen Buchs):**
  * **Angenommen** das Buch ist aktuell ausgeliehen (`Borrowed`) und es gibt noch keine Warteschlange.
  * **Wenn** ein Benutzer das Buch reserviert.
  * **Dann** ist der Vorgang erfolgreich, der Buchzustand bleibt `Borrowed` (mit dem Benutzer als erstem Element in der Warteschlange) und ein `BookReservedEvent` (Position 1) wird zur Benachrichtigung generiert.

* **AC 5.2 (Einreihen in eine bestehende Warteschlange):**
  * **Angenommen** das Buch ist ausgeliehen (`Borrowed`) und Benutzer A steht in der Warteschlange.
  * **Wenn** Benutzer B das Buch ebenfalls reserviert.
  * **Dann** ist der Vorgang erfolgreich, der Buchzustand bleibt `Borrowed`, aber Benutzer B wird ans Ende der bestehenden Warteschlange angehängt. Es wird ein `BookReservedEvent` (Position 2) generiert.

* **AC 5.3 (Doppelte Reservierung durch denselben Benutzer verhindern):**
  * **Angenommen** ein Benutzer steht für dieses Buch bereits in der Warteschlange.
  * **Wenn** genau dieser Benutzer versucht, dasselbe Buch noch einmal zu reservieren.
  * **Dann** schlägt der Vorgang fehl mit dem Fehler "Bereits in der Warteschlange" (`AlreadyInQueue`).

* **AC 5.4 (Reservierung eines verfügbaren Buchs blockieren):**
  * **Angenommen** ein Buch ist frei verfügbar und steht im regulären Regal (`Available(NormalShelf)`).
  * **Wenn** ein Benutzer versucht, dieses Buch über das System zu reservieren.
  * **Dann** schlägt der Vorgang fehl mit dem Fehler "Buch ist verfügbar" (`BookIsAvailable`) – mit dem impliziten Hinweis, es einfach selbst aus dem Regal zu holen.

* **AC 5.5 (Reservierung von Präsenzbestand blockieren):**
  * **Angenommen** ein Buch gehört zum Präsenzbestand (`ReferenceSection`).
  * **Wenn** ein Benutzer versucht, dieses Buch zu reservieren.
  * **Dann** schlägt der Vorgang fehl mit dem Fehler "Nur Präsenzbestand" (`BookIsReferenceOnly`).

* **AC 5.6 (Reservierung eines bereits für mich bereitgestellten Buchs blockieren):**
  * **Angenommen** ein Buch liegt im Abholregal (`ReadyForPickup`) für Benutzer A.
  * **Wenn** Benutzer A versucht, dieses Buch zu reservieren.
  * **Dann** schlägt der Vorgang fehl mit dem Fehler "Liegt bereits für Sie bereit" (`AlreadyReadyForPickup`) – mit dem Hinweis, es am Terminal auszuleihen.
* **AC 5.7 (Reservierung eines selbst ausgeliehen Buchs durch denselben Benutzer verhindern):**
  * **Angenommen** ein Benutzer hat dieses Buch bereits ausgeliehen.
  * **Wenn** genau dieser Benutzer versucht, dasselbe Buch  zu reservieren.
  * **Dann** schlägt der Vorgang fehl mit dem Fehler "Bereits ausgeliehen" (`AlreadyBorrowedByUser`).



## 5. Use Case UC-1: Self-Service Buch ausleihen

* **Primary Actor:** Benutzer (Student oder Professor)
* **Preconditions:**
1. Terminal ist betriebsbereit.
2. Benutzer hat sich per Ausweis am RFID-Reader erfolgreich authentifiziert.


* **Postconditions bei Erfolg:**
1. Das Buch ist auf das Benutzerkonto gebucht.
2. Der Zustand des Buchs ist auf `Borrowed` aktualisiert.
3. Der Diebstahlschutz des RFID-Tags ist deaktiviert.



### Standardablauf (Main Success Scenario)

1. Der Benutzer legt das Buch auf die RFID-Scannermatte.
2. Der RFID-Reader liest die `BookId` ein.
3. Das System prüft die Geschäftsregeln:
* Das Buch ist entleihbar (kein Präsenzbestand, nicht für Dritte reserviert).
* Der Benutzer hat das Ausleihlimit noch nicht erreicht.


4. Das System berechnet die Leihfrist (`DueDate`) anhand der Benutzerrolle:
* `Student`: Aktuelles Datum + 28 Tage.
* `Professor`: Kein Fälligkeitsdatum (`None`).


5. Das System überführt den Zustand des Buches in `Borrowed(UserId, DueDate, Queue)`.
6. Das System erhöht den Zähler der ausgeliehenen Bücher des Benutzers (falls `Student`).
7. Das Terminal zeigt die erfolgreiche Ausleihe visuell an und schaltet das Sicherheitstag frei.

### Extensions (Fehler- & Sonderfälle)

* **1a. Mehrfachausleihe (Auf dem Scanner wurden mehrere Bücher erkannt):**
1. Das System prüft, ob die Ausleihe für alle erkannten Bücher möglich ist, wenn ja:
2. normaler Ablauf, nur für alle erkannten Bücher

* **1b. Mehrfachausleihe mit Fehlern (Auf dem Scanner wurden mehrere Bücher erkannt):**
1. Das System prüft, ob die Ausleihe für alle erkannten Bücher möglich ist, wenn nein:
2. Der Vorgang wird abgebrochen und die fehlermeldung(en) werden dargestellt mit der Aufforderung, die betroffenen Bücher zu entnehmen.



* **3a. Buch gehört zum Handapparat (`ReferenceSection`):**
1. Das System bricht den Vorgang ab.
2. Fehlermeldung: *"Nur Präsenzbestand"* (`BookIsReferenceOnly`).
3. Vorgang wird im Fehlerzustand beendet.


* **3b. Student hat das Limit von 10 Büchern bereits erreicht:**
1. Das System bricht den Vorgang ab.
2. Fehlermeldung: *"Maximales Limit erreicht"* (`MaxBooksLimitReached`).
3. Vorgang wird im Fehlerzustand beendet.


* **3c. Buch ist im Abholregal für eine andere Person hinterlegt (`ReadyForPickup` für `User_X`):**
1. Das System erkennt die Kennung des reservierten Benutzers.
2. Das System bricht den Vorgang ab.
3. Fehlermeldung: *"Für anderen Benutzer reserviert"* (`ReservedForAnotherUser`).
4. Vorgang wird im Fehlerzustand beendet.


* **3d. Buch ist bereits als ausgeliehen markiert (`Borrowed`):**
1. Fehlermeldung: *"Bereits ausgeliehen"* (`AlreadyBorrowed`).
2. Das System bietet die Option zur Vormerkung / Reservierung an (Trigger für US-5).
