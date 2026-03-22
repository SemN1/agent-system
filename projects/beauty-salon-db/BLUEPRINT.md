# Blueprint - Beauty Salon DB
**Creato:** 22 Marzo 2026 | **Owner:** Sem | **Status:** Active

## Idea di Business

Un database europeo di saloni di bellezza che diventa la benzina per una serie di prodotti digitali.

### Prodotto 1 - Marketplace B2C (priorità alta)
Un sito/marketplace dove i consumatori trovano saloni di bellezza vicini a loro.
- Nome da definire
- Dominio da registrare
- Struttura: ricerca per zona, categoria, servizio
- App mobile B2C per consumatori
- Monetizzazione: abbonamenti saloni, commissioni prenotazioni

### Prodotto 2 - SDR Agent (DigaLook)
Outreach commerciale automatizzato verso i saloni.
- Contatto via email/telefono automatizzato
- Proposta di iscrizione al marketplace
- CRM integrato per gestione trattative

### Prodotto 3 - Monitor Competitor
Rileva quando un salone cambia piattaforma (Treatwell, Fresha, ecc.)
- Alert automatici
- Opportunità di acquisizione clienti

### Prodotto 4 - Beauty AI Marketplace
Comparatore con AI - consiglia il salone giusto in base alle preferenze.

## Stack Tecnico
- Database: PostgreSQL (salons_db) - 608k saloni in 10 paesi
- Scraping: Python scrapers su semn1
- Hosting marketplace: da definire
- App mobile: da definire

## KPI Target
- Saloni nel DB: 900k+
- Copertura telefonica: >75%
- Paesi: 10 europei
- Go-live marketplace: da definire

## Roadmap (aggiornata 2026-03-22)

### Fase 1 - Completamento Database (attuale)
**Trigger completamento:** Copertura telefonica >80% su tutti i paesi prioritari

Paesi prioritari in ordine:
1. Italia (attuale 24% tel) - website_scraper in corso
2. Spagna (attuale 11% tel) - da avviare
3. UK (attuale 22% tel) - Booksy scraper da sviluppare
4. Francia (59% tel) - enrichment residuo
5. Germania (51% tel) - enrichment residuo
6. Olanda (36% tel) - enrichment residuo
Nordics: rimandati

**Strategia telefoni mancanti:**
- Ricerca fonti alternative a Google Places (da fare)
- Calcolo costo Google Places per telefoni mancanti (da fare)
- Decisione finale su Google Places dopo calcolo

### Fase 2 - Enrichment
- Deduplicazione fuzzy
- Completamento siti web
- Validazione telefoni

### Fase 3 - Marketplace MVP
**BLOCCATO** fino a DB all'80-90% di completamento
- Nome marketplace da definire
- Dominio da registrare
- Stack tecnico da scegliere

### Fase 4 - Lancio
- Acquisizione saloni
- Marketing

### Fase 5 - App Mobile B2C
- Consumer app
- Prenotazioni
