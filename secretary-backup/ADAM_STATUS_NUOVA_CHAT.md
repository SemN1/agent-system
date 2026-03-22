# ADAM - Stato Completo Progetto
## Documento per continuazione in nuova chat
**Data:** 2026-03-22 | **Chat:** Origin

---

## 1. IDENTITA SISTEMA

- **Progetto:** Origin
- **Agente segretario:** Adam
- **Proprietario:** Sem (Simone)
- **Server:** semn1 / 192.168.1.13 / Ubuntu 24 / GTX 1080 8GB / 32GB RAM

---

## 2. CREDENZIALI (tutte in /home/semn1/origin/.env)

Vedi .env sul server. Non ripetere credenziali in questo file.

---

## 3. SERVIZI ATTIVI
```bash
sudo systemctl status adam            # Agente segretario
sudo systemctl status scraping_agent  # Sub-agent scraping
docker ps                             # n8n, chromadb, anythingllm
```

- adam.service: RUNNING
- scraping_agent.service: RUNNING
- n8n: porta 5678
- chromadb: porta 8000

---

## 4. FILE PRINCIPALI SUL SERVER
```
/home/semn1/origin/
├── adam.py                    # processo Adam v3.0
├── adam_executor.py           # modulo esecuzione comandi
├── scraping_agent.py          # sub-agent scraping autonomo
├── projects/
│   ├── beauty-salon-db/
│   │   ├── BLUEPRINT.md
│   │   ├── STATUS.md
│   │   └── DECISIONS.md
│   └── agent-army/
│       ├── BLUEPRINT.md
│       ├── STATUS.md
│       └── DECISIONS.md
└── .env
```

---

## 5. ARCHITETTURA MULTI-AGENTE

Adam è il CEO. Sem parla solo con Adam.
Sub-agent comunicano via tabella agent_tasks in PostgreSQL.
Quando un agente si blocca, notifica Adam, Adam notifica Sem su Telegram.
Sem risponde con 1/2/3 o testo libero. Adam trasmette al sub-agent.

---

## 6. PROGETTI

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
**Aggiornato:** 22 Marzo 2026

## Stato generale
- Fase: Planning
- GitHub repo: https://github.com/SemN1/Agent-Army
- Sviluppo: non ancora iniziato

## Completato
- Blueprint iniziale definito
- GitHub repo creato

## Bloccato
- Nulla al momento

## Prossimi step
- Definire blueprint tecnico dettagliato
- Decidere stack frontend per onboarding
- Sviluppare primo agente MVP


---

## 7. COSA FUNZIONA AL 100%

1. Adam risponde su Telegram (no parse_mode - evita errori 400)
2. Messaggi lunghi spezzati in chunk da 3500 caratteri
3. Loop proattivo ogni 30 minuti controlla blocchi sub-agent
4. scraping_agent.py gira 24/7 come systemd
5. Flusso completo: Sem -> Adam -> agent_tasks -> sub-agent -> notifica
6. Meeting virtuale per progetto: "meeting beauty salon db"
7. Struttura progetti: Blueprint, Status, Decisions su GitHub
8. Backup notturno alle 3:00 con aggiornamento STATUS.md automatico

---

## 8. COMANDI TELEGRAM FUNZIONANTI

- `status` → stato sistema
- `lancia scraper italia` → avvia scraping
- `meeting beauty salon db` → briefing completo progetto
- `stato agenti` → status tutti i sub-agent
- `1` / `2` / `3` → risposta a blocco sub-agent
- `genera recap` → recap giornaliero manuale

---

## 9. PENDING AL 2026-03-22

- [ ] Rispondere alle domande di Adam sul meeting beauty salon db
- [ ] Decidere timeline e nome marketplace
- [ ] Sviluppare Booksy scraper UK
- [ ] Iniziare Agent Army fase 1

---

## 10. PROMPT PER NUOVA CHAT

Sei Adam, l'agente segretario di Sem nel sistema Origin.
Leggi questo documento e carica anche:
https://raw.githubusercontent.com/SemN1/origin/main/ADAM_KNOWLEDGE_BASE.md

Poi chiedi a Sem cosa vuole fare oggi.
