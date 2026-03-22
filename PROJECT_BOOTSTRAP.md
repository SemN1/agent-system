# PROJECT_BOOTSTRAP.md
## Sistema Origin — Regole Globali per Nuovi Progetti
**Versione:** 2.0 | **Ultimo aggiornamento:** Marzo 2026
**Proprietario:** Sem | **Agente Segretario:** Adam (Origin)

---

## 1. IDENTITÀ DEL SISTEMA

Stai operando all'interno del sistema **Origin** — un network di agenti AI costruito da Sem.
Adam è il CEO e unico punto di contatto tra Sem e tutti i sub-agent.
Sem parla solo con Adam. Adam coordina tutto.

**Gerarchia:**
- Sem → Adam (Telegram @SemnMasterBot)
- Adam → sub-agent per ogni macro-progetto
- Sub-agent lavorano in autonomia 24/7

---

## 2. INFRASTRUTTURA

### Server
```
Host:     semn1 / 192.168.1.13
OS:       Ubuntu 24
GPU:      GTX 1080 8GB
RAM:      32GB
Accesso:  ssh semn1@192.168.1.13
```

### Servizi attivi
```
adam.service            → Adam agente segretario (python3 /home/semn1/origin/adam.py)
scraping_agent.service  → Sub-agent scraping Beauty Salon DB
n8n:        porta 5678
PostgreSQL: porta 5432
ChromaDB:   porta 8000
Ollama:     porta 11434
```

### Credenziali (tutte in /home/semn1/origin/.env)
```
TELEGRAM_BOT_TOKEN      → token SemnMasterBot
TELEGRAM_ALLOWED_USERS  → 2560082 (Sem)
CLAUDE_API_KEY          → API key Anthropic
GITHUB_TOKEN            → token SemN1
GITHUB_USERNAME         → SemN1
OLLAMA_MODEL            → llama3.2:1b
POSTGRES_CONN_STRING    → postgresql://agent_system:1@localhost:5432/agent_hub
SALONS_DB               → postgresql://salon_admin:SalonsDB_2026_Secure!@localhost:5432/salons_db
```

### Path importanti
```
/home/semn1/origin/                        → repo Origin (Adam)
/home/semn1/origin/projects/               → Blueprint/Status/Decisions per progetto
/home/semn1/beauty-salon-db/               → repo Beauty Salon DB
/home/semn1/directory_progetto/scrapers/   → scraper Python
/data/backups/secretary-chat/              → backup snapshot Origin
```

### Database agent_hub — tabelle principali
```
project_status      → stato progetti
agent_tasks         → coda comunicazione Adam ↔ sub-agent
adam_conversations  → memoria conversazioni
adam_memory         → fatti importanti
adam_agents         → registro sub-agent attivi
cost_tracking       → costi Claude API
```

---

## 3. STRUTTURA PROGETTI

Ogni progetto ha tre documenti in /home/semn1/origin/projects/[nome-progetto]/:
```
BLUEPRINT.md    → idea di business, visione, roadmap
STATUS.md       → stato corrente, aggiornato ogni notte automaticamente
DECISIONS.md    → log decisioni prese (append-only, mai cancellare)
```

Repo GitHub dedicato per ogni progetto: github.com/SemN1/[nome-progetto]

---

## 4. ARCHITETTURA MULTI-AGENTE

### Comunicazione Adam ↔ sub-agent
- Adam crea task in tabella agent_tasks (status: pending)
- Sub-agent legge task ogni 5 minuti, esegue, aggiorna status
- Se bloccato: sub-agent scrive block_notification → Adam legge nel loop 30min → notifica Sem
- Sem risponde 1/2/3 o testo → Adam trasmette al sub-agent

### Adam chiede a Sem SOLO per:
1. Scelte architetturali che influenzano il futuro del progetto
2. Costi rilevanti (token Anthropic, API a pagamento, Google Places ecc.)
3. Blocchi che richiedono credenziali o account che solo Sem può creare

### Tutto il resto: autonomia completa

---

## 5. COMANDI TELEGRAM (SemnMasterBot)
```
status                      → overview sistema
lancia scraper [paese]      → avvia scraping
meeting [progetto]          → briefing completo progetto
stato agenti                → status tutti i sub-agent
1 / 2 / 3                   → risposta a blocco sub-agent
genera recap                → recap giornaliero manuale
```

---

## 6. REGOLE GLOBALI

1. Comandi sempre in box separati — mai due comandi nello stesso box
2. GitHub è la memoria — tutto va pushato
3. Backup prima di cambiamenti critici
4. Budget Claude: limite 50 EUR/mese, alert a 40 EUR
5. Credenziali: mai in chiaro nei commit, sempre in .env
6. No Google Places API in automatico — rischio costi esplosivi
7. Sem si chiama Sem (non Simone, non Sam)
8. Adam non chiede permessi per task di routine — agisce e riporta

---

## 7. REPOS GITHUB
```
SemN1/origin          → infrastruttura Adam
SemN1/beauty-salon-db → Beauty Salon DB (scraping + marketplace futuro)
SemN1/Agent-Army      → Agent Army (multi-agent product)
SemN1/ollama-lab      → Ollama Lab (planning)
SemN1/crm-personale   → CRM Personale (planning)
SemN1/personal-rag    → Personal RAG (planning)
```

---

## 8. APRIRE UNA NUOVA CHAT DI PROGETTO

Quando Sem apre una nuova chat Claude per un progetto specifico, incollare:

> Sei un agente AI specializzato nel progetto [NOME].
> Leggi questi file e inizia:
> 1. https://raw.githubusercontent.com/SemN1/origin/main/PROJECT_BOOTSTRAP.md
> 2. https://raw.githubusercontent.com/SemN1/origin/main/projects/[nome]/BLUEPRINT.md
> 3. https://raw.githubusercontent.com/SemN1/origin/main/projects/[nome]/STATUS.md
>
> [DESCRIZIONE IDEA DI BUSINESS O PRIMO TASK]

---

## 9. TEMPLATE NUOVO PROGETTO

*(Compilare quando si lancia un nuovo progetto)*
```
Nome Progetto:    [DA COMPILARE]
Project ID:       [DA COMPILARE]
GitHub Repo:      SemN1/[DA COMPILARE]
Obiettivo:        [DA COMPILARE]
Sub-agent:        [DA COMPILARE]
Prima cosa:       [DA COMPILARE]
```

---

*Mantenuto da Adam. Ultima versione su:*
*https://github.com/SemN1/origin/blob/main/PROJECT_BOOTSTRAP.md*
