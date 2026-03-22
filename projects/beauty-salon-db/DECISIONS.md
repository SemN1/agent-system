# Decision Log - Beauty Salon DB
**Progetto:** Beauty Salon DB

---

## 2026-03-22 - No Google Places API in automatico
**Decisione:** Non usare Google Places API in modo automatico.
**Motivo:** Rischio costi esplosivi - addebitati 100 EUR per errore in passato.
**Alternativa:** Usare solo quando strettamente necessario e con limiti espliciti.

## 2026-03-22 - Architettura scraping autonoma
**Decisione:** scraping_agent.py gira come systemd 24/7 e comunica con Adam via PostgreSQL.
**Motivo:** Sem non deve fare nulla manualmente - tutto autonomo.
**Impatto:** Ogni errore viene segnalato ad Adam che notifica Sem su Telegram.

## 2026-03-22 - Path scraper
**Decisione:** Gli scraper vivono in /home/semn1/directory_progetto/scrapers/
**Motivo:** Path storico, non spostare per evitare rotture.

## 2026-03-22 - Priorità geografiche scraping
**Decisione:** Focus su paesi già presenti nel DB.
**Priorità:** Italia, Spagna, Francia, Germania, UK, Olanda.
**Nordics:** Rimandati a futuro.
**Motivo:** Consolidare quello che abbiamo prima di espandere.

## 2026-03-22 - Booksy scraper UK
**Decisione:** Sviluppare Booksy scraper subito.
**Motivo:** UK ha solo 22% copertura telefonica, Booksy è fonte principale.
**Azione:** Adam commissionerà sviluppo scraper a scraping_agent.

## 2026-03-22 - Strategia telefoni mancanti
**Decisione:** Fare ricerca su alternative a Google Places per telefoni mancanti.
**Motivo:** Google Places ha rischio costi esplosivi (100 EUR addebitati per errore in passato).
**Azioni:**
1. Ricerca fonti alternative gratuite/economiche per telefoni
2. Calcolare costo esatto Google Places per coprire tutti i telefoni mancanti
3. Decidere poi se usarlo o no in base al calcolo

## 2026-03-22 - Timeline marketplace
**Decisione:** Marketplace in backlog fino a database all'80-90% di completamento.
**Motivo:** Il DB è la benzina del business. Non costruire il motore prima di avere carburante.
**Trigger per sblocco:** Copertura telefonica >80% su tutti i paesi prioritari.
