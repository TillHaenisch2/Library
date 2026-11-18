# Bibliothek: Self-Service-Ausleihe – Ziel und Umgebung


## 1. Ausgangslage

Die Bibliothek der Hochschule verleiht heute ausschließlich an der Ausleihtheke. Der Bestand ist vollständig mit RFID-Tags (HF, ISO 15693) ausgestattet. An den Ausgängen stehen RFID-Sicherungsgates, zukünftig wird es auch einen Rückgabeautomaten geben (out of scope für dieses Projekt)

Katalog, Benutzerkonten, Gebühren und Mahnwesen liegen im **Bibliotheksmanagementsystem (LMS, Horizon)** eines Bibliotheksverbunds, das als gehosteter Dienst betrieben wird. Die Hochschule kann es nicht verändern, nur über seine Schnittstellen nutzen.

## 2. Ziele

### Projektziel

Benutzer leihen Bücher selbstständig an Self-Service-Terminals aus und merken ausgeliehene Bücher vor, ohne dass Personal beteiligt ist. Die Anforderungen im Detail sind in req.md definiert.



### Abgrenzung

* Kein Ersatz oder Erweiterung des LMS (Katalog, Erwerbung, Mahnwesen, Gebühren)
* Keine Rückgabe am Terminal (zunächst an der Theke später an einem Rückgabeautomaten)
* Payment separat
* Recherche separat
* Fernleihe, Medien außer Büchern (z. B. Laptops) an der Theke

## 3. Stakeholder
siehe req.md

## 4. Systemabgrenzung

**Zum System gehören:**
* die Self-Service-Terminals: Gehäuse, Touchscreen, Lautsprecher, HF-RFID-Reader (Ablagefläche für bis zu 5 Bücher, NFR-P2) und die Terminal-Software
* die Ansteuerung des RFID-Readers: Tags lesen, Diebstahlschutz deaktivieren (FR-5.1), ist also kein externen Akteur.

**Fachlicher Umfang:** Ausleihe (UC-1, US-1 bis US-4) (Epic 1), Vormerkung mit Warteschlange (US-5)(Epic 2), Abholung aus dem Abholregal, Sitzungsverwaltung (US-6) (Epic 1), Benachrichtigung bei Abholbereitschaft (FR-4.3) (Epic 2).

**Nicht zum System gehören:**

* **Rückgabe:** Die Rückgabe erfolgt zukünftig (nicht im scope des Projekts) an einem Rückgabeautomaten, derzeit an der Theke. Beide buchen direkt im LMS und reaktivieren den Diebstahlschutz. Die SSA muss von Rückgaben aber **erfahren**, weil FR-4.3 (Abholregal, Benachrichtigung) davon abhängt. *Festlegung*: Rückgabe ist außerhalb des Systems. Wie die SSA davon erfährt, ist offen.
* **Bereitstellen ins Abholregal:** Das Thekenpersonal stellt zurückgegebene Bücher ein und legt vorgemerkte Bücher ins Abholregal (Zustand `Returned` → `ReadyForPickup` im Zustandsmodell). Dazu nutzt es ein Werkzeug. Ob dieses Werkzeug zur SSA gehört (kleine Web-Oberfläche) oder das LMS-Client ist, ist offen.

* **Externe Systeme**
* Katalog, Exemplardaten, Benutzerkonten, Gebühren, Mahnwesen (LMS)
* Sicherungsgates, Rückgabeautomat
* Ausweisverwaltung (Campus-Karte, IdM)
* Reservierung/Vormerkung (Web-Schnittstelle)
* Vormerken und Stornieren sind am Terminal möglich (z. B. nach Fehlern), während das externe Web-Portal lediglich ein zusätzlicher Online-Kanal ins LMS ist
