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

## 2026-03-22 - Strategia enrichment telefoni mancanti
**Decisione:** Approccio a tre fasi per i ~270k saloni senza telefono.

**Fase 1 - Fonti gratuite (priorità):**
- Yelp Fusion API: UK, Germania, Francia (500 richieste/giorno gratis)
- Foursquare Places API: tutti i paesi (200 richieste/giorno gratis)
- Website scraper: già in corso su Italia
- Booksy scraper: UK (da sviluppare)
Stima recupero: +80.000 telefoni a costo zero.

**Fase 2 - Google Places solo se necessario:**
- Costo calcolato: ~€715 una tantum per 270k richieste
- Da usare SOLO dopo aver esaurito fonti gratuite
- Hard cap obbligatorio su Google Cloud Console: €200/mese max
- Mai in automatico senza approvazione esplicita di Sem

**Motivo:** Rischio costi esplosivi documentato (€100 addebitati per errore in passato).
**Trigger per Google Places:** Copertura telefonica <70% dopo Fase 1.

## 2026-03-23 - Usare Claude API, non Ollama
**Decisione:** Adam usa SEMPRE Claude API (claude-sonnet-4-20250514). Ollama non viene usato.
**Motivo:** Ollama troppo lento su GTX 1080. Claude API da risposte di qualita superiore.
**Impatto:** Tutti i comandi in adam.py chiamano ask_claude(), mai ask_ollama().

## 2026-03-23 - Adam v3.0 architettura completa
**Decisione:** Adam gira come systemd con thread monitor sub-agent ogni 30 minuti.
**Componenti:**
- adam.py v3.0: loop Telegram + thread monitor + planner integrato
- adam_planner.py: trasforma linguaggio naturale in azioni JSON eseguibili
- adam_executor.py: esecuzione comandi server
- scraping_agent.py: sub-agent autonomo per beauty-salon-db

## 2026-03-23 - Parse mode Markdown disabilitato su Telegram
**Decisione:** Nessun parse_mode nei messaggi Telegram di Adam.
**Motivo:** Causa errori 400 con codice Python e caratteri speciali.

## 2026-03-23 - Planner per comandi complessi
**Decisione:** Comandi lunghi (>30 caratteri con verbi d'azione) vanno al planner.
**Funzionamento:** should_use_planner() -> generate_plan() Claude -> execute_step() per ogni passo.
**Limite attuale:** generate_code con max_tokens 4096 ancora insufficiente per scraper lunghi.
