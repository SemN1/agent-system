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
