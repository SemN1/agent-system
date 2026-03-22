# ADAM - Stato Completo Progetto
## Documento per continuazione in nuova chat
**Data:** 2026-03-22 | **Chat:** Origin

---

## 1. IDENTITA SISTEMA

- Progetto: Origin
- Agente segretario: Adam v3.0
- Proprietario: Sem
- Server: semn1 / 192.168.1.13 / Ubuntu 24 / GTX 1080 8GB / 32GB RAM

---

## 2. CREDENZIALI

Tutte in /home/semn1/origin/.env — non ripetere qui.
YELP_API_KEY: da aggiungere (Yelp aveva problemi il 22/03/2026, riprovare)

---

## 3. SERVIZI ATTIVI

- adam.service: RUNNING (v3.0 con loop proattivo + planner)
- scraping_agent.service: RUNNING (autonomo 24/7)
- n8n: porta 5678
- chromadb: porta 8000

---

## 4. FILE PRINCIPALI
```
/home/semn1/origin/
├── adam.py                    # v3.0 - loop proattivo + planner integrato
├── adam_executor.py           # esecuzione comandi server
├── adam_planner.py            # planner linguaggio naturale -> azioni
├── scraping_agent.py          # sub-agent scraping autonomo
├── new_project.py             # crea nuovo progetto in 30 secondi
├── generate_status_now.py     # genera questo documento
├── projects/
│   ├── beauty-salon-db/       # BLUEPRINT, STATUS, DECISIONS
│   └── agent-army/            # BLUEPRINT, STATUS, DECISIONS
├── PROJECT_BOOTSTRAP.md       # v2.0 - regole globali sistema
└── .env                       # tutte le credenziali
```

---

## 5. ARCHITETTURA MULTI-AGENTE

- Adam e' il CEO. Sem parla solo con Adam su Telegram (@SemnMasterBot)
- Sub-agent comunicano via agent_tasks in PostgreSQL
- Blocchi -> Adam notifica Sem -> Sem risponde 1/2/3 -> Adam trasmette
- Planner: comandi linguaggio naturale -> piano JSON -> esecuzione autonoma

---

## 6. COSA FUNZIONA AL 100%

1. Adam risponde su Telegram (no parse_mode)
2. Messaggi lunghi in chunk da 3500 caratteri
3. Loop proattivo ogni 30 minuti
4. scraping_agent autonomo 24/7
5. Flusso task Adam -> agente -> notifica blocco -> risposta umana
6. Meeting virtuale: "meeting beauty salon db"
7. Struttura progetti Blueprint/Status/Decisions su GitHub
8. Backup notturno alle 3:00
9. Planner: comandi complessi eseguiti in autonomia
10. new_project.py: nuovo progetto in 30 secondi

---

## 7. COMANDI TELEGRAM

- status -> overview sistema
- meeting [progetto] -> briefing completo
- lancia scraper [paese] -> avvia scraping
- stato agenti -> status sub-agent
- 1/2/3 -> risposta blocco sub-agent
- genera recap -> recap manuale
- [qualsiasi comando complesso] -> planner lo esegue in autonomia

---

## 8. PROGETTI

### Beauty Salon DB
# Status - Beauty Salon DB
**Aggiornato:** 22 Marzo 2026

## Database
- Totale saloni: 608.024
- Paesi: 10 (Germania, Francia, Belgio, Italia, UK, Spagna, Olanda, Austria, Portogallo, Svizzera)
- Copertura telefonica: ~55%

## Distribuzione per paese
| Paese | Saloni | Tel% |
|-------|--------|------|
| Germania | 234.288 | 51% |
| Francia | 214.879 | 59% |
| Belgio | 42.060 | 62% |
| Italia | 36.779 | 24% |
| UK | 36.184 | 22% |
| Spagna | 26.351 | 11% |

## Scraping in corso
- website_scraper: attivo su Italia
- scraping_agent: running su semn1 come systemd

## Prossimi step
- Completare Italia, UK, Spagna con website_scraper
- Sviluppare Booksy scraper per UK
- Deduplicazione fuzzy
- Enrichment telefoni mancanti


### Agent Army
# Status - Agent Army
**Aggiornato:** 2026-03-22

## Stato
planning

## Fase Corrente
Setup iniziale

## Ultimo Step Completato
Progetto creato

## Prossimo Step
Definire blueprint dettagliato con idea di business

## Blocchi
Nessuno

## Metriche
- Data creazione: 2026-03-22


---

## 9. PENDING PER DOMANI

- [ ] Ottenere Yelp API Key (yelp.com/developers aveva problemi il 22/03)
- [ ] Aggiungere YELP_API_KEY in /home/semn1/origin/.env
- [ ] Testare yelp_scraper.py su UK
- [ ] Aggiungere Foursquare come seconda fonte telefoni gratuita
- [ ] Testare planner con comandi piu complessi
- [ ] Aprire chat Agent Army con new_project.py

---

## 10. SCRAPER DISPONIBILI
```
/home/semn1/directory_progetto/scrapers/
├── website_scraper.py     # in corso su Italia
├── yelp_scraper.py        # pronto, manca API key
├── treatwell.py
├── fresha.py
├── planity.py
├── overpass_enrichment.py
└── ...
```

---

## 11. PROMPT PER NUOVA CHAT

Sei Adam, l'agente segretario di Sem nel sistema Origin.
Leggi questo documento e carica anche:
https://raw.githubusercontent.com/SemN1/origin/main/ADAM_KNOWLEDGE_BASE.md

Poi chiedi a Sem cosa vuole fare oggi.
