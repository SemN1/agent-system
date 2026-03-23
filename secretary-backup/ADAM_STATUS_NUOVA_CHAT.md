# ADAM - Stato Completo Progetto
## Documento per continuazione in nuova chat
**Data:** 2026-03-23 | **Chat:** Origin

---

## 1. IDENTITA SISTEMA

- Progetto: Origin
- Agente segretario: Adam v3.0
- Proprietario: Sem
- Server: semn1 / 192.168.1.13 / Ubuntu 24 / GTX 1080 8GB / 32GB RAM

---

## 2. DECISIONI ARCHITETTURALI CRITICHE (leggile tutte)

### LLM: SOLO Claude API, mai Ollama
Adam usa SEMPRE e SOLO Claude API (claude-sonnet-4-20250514).
Ollama e' installato ma NON viene usato da Adam — troppo lento su GTX 1080.
La funzione needs_claude() ritorna sempre True.
NON suggerire mai di usare Ollama per i task di Adam.

### Telegram: nessun parse_mode
I messaggi Telegram non usano parse_mode Markdown.
Causa errori 400 con codice Python. Rimosso definitivamente.

### Architettura sub-agent
- Adam crea task in agent_tasks (PostgreSQL)
- scraping_agent.py legge task ogni 5 minuti ed esegue
- Blocchi -> block_notification -> Adam notifica Sem su Telegram
- Sem risponde 1/2/3 -> Adam trasmette al sub-agent

### Planner linguaggio naturale
Comandi complessi (>30 char con verbi d'azione) vanno a adam_planner.py
Il planner chiama Claude, genera piano JSON, esegue i passi in autonomia.
Sem non deve fare nulla — Adam agisce e riporta.

### Adam chiede a Sem SOLO per
1. Scelte architetturali che influenzano il futuro
2. Costi rilevanti (Google Places, API a pagamento)
3. Blocchi che richiedono credenziali che solo Sem puo creare

---

## 3. CREDENZIALI

Tutte in /home/semn1/origin/.env
YELP_API_KEY: DA AGGIUNGERE (yelp.com aveva problemi il 22/03 — riprovare domani)

---

## 4. SERVIZI
```
adam.service              RUNNING  (v3.0)
scraping_agent.service    RUNNING  (autonomo 24/7)
n8n                       porta 5678
chromadb                  porta 8000
```

---

## 5. FILE PRINCIPALI
```
/home/semn1/origin/
├── adam.py                    v3.0 - loop + monitor thread + planner
├── adam_planner.py            planner linguaggio naturale
├── adam_executor.py           esecuzione comandi server
├── scraping_agent.py          sub-agent scraping autonomo
├── new_project.py             crea nuovo progetto in 30 secondi
├── generate_status_now.py     rigenera questo documento
├── projects/
│   ├── beauty-salon-db/       BLUEPRINT + STATUS + DECISIONS
│   └── agent-army/            BLUEPRINT + STATUS + DECISIONS
└── PROJECT_BOOTSTRAP.md       v2.0 regole globali

Scrapers in: /home/semn1/directory_progetto/scrapers/
├── website_scraper.py         IN CORSO su Italia
├── yelp_scraper.py            PRONTO - manca YELP_API_KEY in .env
└── ...altri scraper
```

---

## 6. COMANDI TELEGRAM (@SemnMasterBot)
```
status                    overview sistema
meeting [progetto]        briefing completo (es: meeting beauty salon db)
lancia scraper [paese]    avvia scraping
stato agenti              status sub-agent
1 / 2 / 3                 risposta a blocco sub-agent
genera recap              recap manuale
[comando complesso]       il planner lo esegue in autonomia
```

---

## 7. PROGETTI

### beauty-salon-db (ACTIVE)
- 608.024 saloni in 10 paesi europei
- Copertura telefonica: ~55% (target >80%)
- Scraping in corso: website_scraper su Italia
- Strategia telefoni: Yelp API (gratis) -> Foursquare (gratis) -> Google Places (ultimo resort, ~715 EUR)
- Marketplace: IN BACKLOG fino a DB all'80-90%
- Priorita paesi: Italia, Spagna, UK, Francia, Germania, Olanda

### agent-army (PLANNING)
- Sistema multi-agente packaged per aziende medio-grandi
- Marketplace 300 agenti, onboarding freemium, video diagnostico AI
- GitHub: SemN1/Agent-Army
- Sviluppo non ancora iniziato

---

## 8. PENDING PER DOMANI

- [ ] Ottenere Yelp API Key (yelp.com/developers/v3/manage_app)
- [ ] Aggiungere YELP_API_KEY in /home/semn1/origin/.env
- [ ] Testare yelp_scraper.py su UK
- [ ] Aggiungere Foursquare come seconda fonte telefoni gratuita
- [ ] Aprire chat Agent Army (usare new_project.py --id agent-army)
- [ ] Testare planner con altri comandi complessi

---

## 9. COME APRIRE NUOVA CHAT

1. Scarica questo file dal server:
   cat /home/semn1/origin/secretary-backup/ADAM_STATUS_NUOVA_CHAT.md

2. Apri nuova chat su claude.ai

3. Allega il file e incolla:
   Sei Adam, l agente segretario di Sem nel sistema Origin.
   Leggi il documento allegato e carica anche:
   https://raw.githubusercontent.com/SemN1/origin/main/ADAM_KNOWLEDGE_BASE.md
   Poi dimmi che hai caricato tutto e chiedimi cosa voglio fare oggi.

---

## 10. NOTA IMPORTANTE PER LA NUOVA CHAT

Questa e' la chat Origin — il punto zero del sistema.
Adam NON usa Ollama. Adam usa SEMPRE Claude API.
Non suggerire mai di usare Ollama, qwen, llama o altri modelli locali per i task di Adam.
Il sistema e' operativo al 85% — manca solo Yelp API key e test planner avanzati.
