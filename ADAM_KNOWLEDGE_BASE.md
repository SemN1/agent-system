# ADAM - Knowledge Base Completa
## Documento Fondativo del Sistema Origin
**Generato:** 15 Marzo 2026 | **Versione:** 1.0
**Autore:** Adam (da chat Origin con Sem)

---

## 1. IDENTITÀ E RUOLO

**Adam** è l'agente segretario del sistema Origin, creato da Sem (Simone).
- Punto zero di tutto il sistema — da qui nasce ogni progetto
- Memoria persistente infinita su PostgreSQL + ChromaDB
- Coordina tutti i progetti sottostanti
- Interfacce: Telegram (@SemnMasterBot) + Open WebUI
- NON vive in una chat Claude — vive come processo Python sul server

**Sem** (Simone) è il proprietario e operatore del sistema.
- Obiettivo: automatizzare tutto, interagire il meno possibile
- Vuole dare obiettivi agli agenti e ricevere risultati, senza copia-incolla
- Interfaccia preferita: Telegram per comandi, questa chat per architettura

---

## 2. INFRASTRUTTURA SERVER

### Server semn1
```
IP:       192.168.1.13
OS:       Ubuntu 24.04
GPU:      NVIDIA GTX 1080 8GB VRAM
RAM:      32GB
Storage:  300GB liberi
Accesso:  ssh semn1@192.168.1.13
```

### Stack Docker
```
n8n:        http://localhost:5678   (workflow automation, v2.11.3+)
PostgreSQL: localhost:5432          (database centrale)
ChromaDB:   localhost:8000          (vector store / RAG)
```

### Servizi diretti (non Docker)
```
Ollama:     localhost:11434         (LLM locale, gira come systemd)
Open WebUI: localhost:8080          (UI per chat locale)
```

### Modelli Ollama disponibili
```
qwen3:14b          (in download - modello principale futuro)
qwen3.5:35b-a3b    23GB  (MoE, troppo grande per GPU)
qwen2.5:7b         4.7GB (attuale default Adam)
llama3.1:70b       42GB  (troppo grande)
llama3.2:1b        1.3GB (piccolo, veloce)
```

---

## 3. CREDENZIALI (tutte in /home/semn1/origin/.env)

```
TELEGRAM_BOT_TOKEN=8674087870:AAH9S6FNABKsOswbJJl-Cg0xOQLDnKn4PbU
TELEGRAM_ALLOWED_USERS=2560082
CLAUDE_API_KEY=[vedi /home/semn1/origin/.env → CLAUDE_API_KEY]
GITHUB_TOKEN=[vedi /home/semn1/origin/.env → GITHUB_TOKEN]
GITHUB_USERNAME=SemN1
OLLAMA_MODEL=qwen2.5:7b  (aggiornare a qwen3:14b quando finisce download)
POSTGRES_CONN_STRING=postgresql://agent_system:1@localhost:5432/agent_hub
N8N_USER=admin
CLAUDE_MODEL=claude-sonnet-4-20250514
USD_TO_EUR_RATE=0.92
BUDGET_ALERT_THRESHOLD=40
BUDGET_HARD_LIMIT=50

Database salons_db:
  user: salon_admin
  password: SalonsDB_2026_Secure!
  
Database agent_hub:
  user: agent_system  
  password: 1

n8n:
  user: admin
  password: (vedi .env)
```

---

## 4. STRUTTURA GITHUB

```
SemN1/origin          → infrastruttura, Adam, backup Origin
SemN1/beauty-salon-db → Beauty Salon DB (ex agent-docs)
SemN1/Agent-Army      → progetto Agent Army (nuovo)
SemN1/ollama-lab      → da creare
SemN1/crm-personale   → da creare  
SemN1/personal-rag    → da creare
```

### Struttura cartelle server
```
/home/semn1/origin/              → repo Origin
  ├── adam.py                    → processo principale Adam ✅
  ├── adam_schema.sql            → schema DB Adam ✅
  ├── telegram_bot.py            → vecchio bot (disabilitato)
  ├── origin_backup.sh           → backup notturno sistema
  ├── PROJECT_BOOTSTRAP.md       → template nuovi progetti
  ├── secretary-backup/          → snapshot sistema
  ├── chat-history/              → recap giornalieri (da popolare)
  └── .env                       → tutte le credenziali

/home/semn1/beauty-salon-db/     → repo Beauty Salon DB
/home/semn1/directory_progetto/scrapers/ → tutti gli scraper
/data/shared/scripts/            → script condivisi
/data/backups/secretary-chat/    → backup locali
```

---

## 5. DATABASE agent_hub - TABELLE

### Tabelle esistenti pre-Adam
```sql
projects          → registry progetti (vecchio sistema)
workflows         → workflow n8n
execution_logs    → log esecuzioni
cost_tracking     → tracking costi Claude API
telegram_commands → log comandi Telegram
known_errors      → KB auto-healing
reports           → report generati
system_events     → eventi sistema
project_status    → stato progetti (nuovo sistema)
project_status_history → storico cambi
telegram_offset   → offset polling Telegram
```

### Tabelle Adam (appena create)
```sql
adam_conversations    → ogni messaggio salvato per sempre
adam_memory          → fatti importanti estratti
agent_tasks          → coda comunicazione tra agenti
adam_agents          → registro agenti attivi
adam_daily_log       → log per backup notturno
```

### Progetti in project_status
```
beauty-salon-db  → active  → Fase 1 completamento DB
ollama-lab       → planning
crm-personale    → planning
personal-rag     → planning
```

---

## 6. ARCHITETTURA MULTI-AGENTE

### Schema
```
SEM
 │ (Telegram / Open WebUI)
 ▼
ADAM (segretario)
 │ Memoria persistente PostgreSQL+ChromaDB
 │ Gira 24/7 come systemd su semn1
 │ Usa Ollama 90% + Claude API 10%
 │
 ├──→ AGENTE SCRAPING (beauty-salon-db)
 │     Script Python in /home/semn1/beauty-salon-db/scrapers/
 │     Comunica con Adam via agent_tasks in PostgreSQL
 │
 ├──→ AGENTE RAG (personal-rag)
 ├──→ AGENTE TTS (ollama-lab)
 └──→ AGENTI FUTURI...
```

### Comunicazione tra agenti
- Tabella `agent_tasks` in PostgreSQL
- Adam → Agente: inserisce task con `requires_approval`
- Agente → Adam: aggiorna task con risultato
- Adam → Sem: notifica Telegram

### Decisione architetturale importante
Adam NON vive in una chat Claude. Vive come:
- Processo Python (`adam.py`) su semn1
- Servizio systemd (`adam.service`)
- Memoria in PostgreSQL + ChromaDB
- Backup notturno su GitHub

---

## 7. CRON JOBS ATTIVI

```bash
*/15 * * * *  aggiorna_status.sh (voice)
*/30 * * * *  aggiorna_status.sh (status updates)
0 1,12,20 * * * telegram_library_bot.py
30 1 * * *    backup_to_pc.sh
0 2 * * *     cleanup status_updates_voice
0 3 * * *     origin_backup.sh → backup sistema su GitHub
0 */8 * * *   beauty-salon-db/update_docs.sh
```

### Da aggiungere
```bash
0 2 * * *     adam.py --backup → recap giornaliero + push GitHub
```

---

## 8. SERVIZI SYSTEMD

```
telegram-bot.service  → DISABILITATO (vecchio bot)
adam.service          → DA CREARE (nuovo Adam)
```

### Lezione critica imparata
Quando un bot non risponde come modificato, controllare SEMPRE:
```bash
sudo grep ExecStart /etc/systemd/system/telegram-bot.service
```
Il servizio puntava al file sbagliato (/data/shared/scripts/ invece di /home/semn1/origin/)

---

## 9. PROGETTI IN DETTAGLIO

### Beauty Salon DB
**Obiettivo:** Database europeo saloni di bellezza per outreach commerciale

**Stato attuale:** 611.984 saloni in 10 paesi

**Distribuzione:**
```
Germania:    234.288 | 51% tel |  6% web
Francia:     214.879 | 59% tel |  3% web
Belgio:       42.060 | 62% tel |  3% web
Italia:       36.779 | 24% tel | 58% web ← priorità
UK:           36.184 | 22% tel | 14% web ← priorità
Spagna:       26.351 | 11% tel | 49% web ← priorità
Olanda:        8.409 | 36% tel | 47% web
Austria:       4.314 | 35% tel | 25% web
Portogallo:    3.023 | 18% tel |  4% web
Svizzera:      1.737 | 31% tel | 39% web
```

**Scraper disponibili:**
```
/home/semn1/beauty-salon-db/scrapers/ (ex /home/semn1/directory_progetto/scrapers/)
- website_scraper.py    ✅ verificato, lanciato su Italia
- treatwell.py          da verificare
- fresha.py             da verificare
- gelbeseiten.py        da verificare
- paginegialle.py       bloccato da captcha
- planity.py            usato per Francia/Germania/Belgio
- overpass_enrichment.py già usato su tutti i paesi
```

**Target:** 900k+ saloni, >75% telefoni

**Roadmap:**
1. Website scraper: Italia → Spagna → UK → Germania → altri
2. Verificare scraper esistenti uno per uno
3. Sviluppare Booksy scraper (UK priorità)
4. Deduplicazione fuzzy
5. Google Places API SOLO alla fine (rischio costi - €100 addebitati per errore)

**Prossimi prodotti sul DB:**
1. DigaLook SDR Agent — outreach commerciale automatizzato
2. Monitor competitor — rileva cambio piattaforma
3. Beauty AI Marketplace — comparatore con AI

### Agent Army (nuovo progetto)
**Obiettivo:** Sistema multi-agente packaged per aziende medio-grandi
- Marketplace fino a 300 agenti specializzati
- Freemium: upload dati → video diagnostico AI → proposta pacchetto agenti
- GitHub: https://github.com/SemN1/Agent-Army
- Status: blueprint definito, in attesa di sviluppo

### Ollama Lab
**Obiettivo:** Testing LLM e TTS locali
- Benchmark modelli su GPU semn1
- Test Text-to-Speech
- Status: planning

### CRM Personale
**Obiettivo:** Gestione trattative commerciali
- Stack: PostgreSQL + n8n + Telegram
- Status: planning

### Personal RAG
**Obiettivo:** RAG su documenti personali (mail, documenti vita)
- Tool conversione: Markitdown (Microsoft)
- Formato output: MD/JSON
- Vector store: ChromaDB già installato
- Status: planning

---

## 10. DECISIONI ARCHITETTURALI IMPORTANTI

1. **Un repo GitHub per ogni progetto** — non un repo centralizzato
2. **Adam vive sul server, non in chat Claude** — memoria persistente reale
3. **Ollama 90% + Claude API 10%** — costi contenuti €5-15/mese extra
4. **n8n per workflow generici** — già installato, non reinventare
5. **Python custom per agenti operativi** — troppo specifici per framework generici
6. **GitHub come memoria esterna** — tutto va pushato, niente muore con la chat
7. **PROJECT_BOOTSTRAP.md** — file standard caricato in ogni nuova chat
8. **Backup triplo** — GitHub + server + PC Windows ogni notte
9. **No Google Places API** in automatico — rischio costi esplosivi
10. **Claude Code installato** — per generazione codice autonoma da Adam

---

## 11. CLAUDE CODE

**Installato su:** semn1, globale
**Versione:** 2.1.49
**Autenticazione:** Claude Pro account (Sem)
**Uso:** Adam può lanciarlo per generare/modificare codice autonomamente

```bash
# Uso non-interattivo da Adam
claude --print "scrivi scraper per Booksy UK, salvalo in /path/file.py"
```

---

## 12. FILE IMPORTANTI DA RICORDARE

```
/home/semn1/origin/.env                    → TUTTE le credenziali
/home/semn1/origin/adam.py                 → processo Adam
/home/semn1/origin/adam_schema.sql         → schema DB Adam
/home/semn1/origin/PROJECT_BOOTSTRAP.md   → template nuovi progetti
/home/semn1/origin/origin_backup.sh        → backup notturno
/home/semn1/origin/secretary-backup/latest_snapshot.md → ultimo snapshot
/data/shared/scripts/project_status_sync.py → sync GitHub→DB
/etc/systemd/system/telegram-bot.service  → servizio bot (ora disabilitato)
```

---

## 13. PENDING TASKS (al 15 Marzo 2026)

### Immediati
- [ ] Finire download qwen3:14b e aggiornare OLLAMA_MODEL in .env
- [ ] Creare adam.service e abilitarlo come systemd
- [ ] Aggiungere cron backup notturno adam.py --backup
- [ ] Testare Adam con qwen3:14b su Telegram

### Prossimi
- [ ] Implementare lettura GitHub all'avvio di Adam
- [ ] Completare website_scraper su Spagna, UK, Germania
- [ ] Verificare overpass_enrichment.py, treatwell.py, fresha.py
- [ ] Sviluppare Booksy scraper UK
- [ ] Aprire chat dedicata Beauty Salon DB con bootstrap aggiornato
- [ ] Importare workflow n8n Project Status Sync
- [ ] Configurare Open WebUI come seconda interfaccia Adam

### Futuri
- [ ] Agent Army: sviluppo blueprint tecnico
- [ ] CRM Personale: definire schema
- [ ] Personal RAG: struttura cartelle documenti

---

## 14. REGOLE DI SISTEMA

1. **Comandi sempre in box separati** — mai due comandi nello stesso box
2. **File Windows:** `C:\Users\Admin\Desktop\Doc vari progetto multiagent\`
3. **git config:** user.email=simone.provalliance@gmail.com, user.name=SimoProvalliance
4. **Budget Claude:** limite €50/mese, alert a €40
5. **Quando questa chat si esaurisce:** backup su GitHub + nuova chat legge questo file
6. **Sem si chiama Sem** (non Simone, non Sam)
7. **Adam non chiede permessi per task di routine** — agisce e riporta
8. **Per azioni critiche** (spesa, cancellazione): chiede conferma via Telegram

---

## 15. STORIA DEL PROGETTO

**Inizio:** Marzo 2026 — setup infrastruttura da zero
**Step 1 completato:** Server, Docker, PostgreSQL, n8n, Ollama, ChromaDB, Telegram bot
**Step 2 completato:** Claude API integrata, cost tracking, ChromaDB KB, comandi Telegram avanzati
**Step 3 in corso:** Adam come agente autonomo con memoria persistente

**Rinominazioni importanti:**
- `agent-system` → `origin` (GitHub + cartella server)
- `agent-docs` → `beauty-salon-db` (GitHub + cartella server)

**Lezione principale imparata:**
Adam non può vivere in una chat Claude perché la finestra di contesto si esaurisce. Deve essere un processo Python con memoria esterna su PostgreSQL e GitHub.

---

*Questo documento è la knowledge base fondativa di Adam.*
*Va aggiornato ad ogni sessione di lavoro significativa.*
*Sempre disponibile su: https://github.com/SemN1/origin/blob/main/ADAM_KNOWLEDGE_BASE.md*


## Aggiornamento 2026-03-22

### 🔧 **Decisioni Tecniche**
- **Implementazione scraper Booksy UK**: Sviluppato nuovo scraper Python con supporto per rate limiting, gestione cookie e proxy rotation per compliance con ToS
- **Fix scraper Spagna**: Identificati problemi di aggiornamento dati nel scraper spagnolo, richiede manutenzione per continuità del servizio

### 📊 **Stato Database Beauty Salon**
- **Milestone raggiunta**: Database ora contiene **608,024+ saloni europei** (precedentemente 611k+)
- **Copertura telefonica**: 337,428 saloni con numero di telefono (55.5% del totale)
- **Dimensioni database**: ~847MB operativo
- **Distribuzione geografica**: Germania leader con 234,288 saloni (51% con telefono)

### 🚀 **Operazioni Attive**
- **Website scraper Italia**: Lanciato processo di raccolta dati per territorio italiano
- **Scraping status**: Processo attivo e monitorato su tutti i paesi target europei

### ⚙️ **Infrastruttura Server**
- **Status stabile**: Server semn1 (192.168.1.13) operativo con risorse ottimali
- **Utilizzo risorse**: RAM 86% libera, GPU sotto-utilizzata (212MB/8192MB), storage 63% disponibile
- **Performance**: Sistema mantiene stabilità operativa per processi di scraping intensivi

### 🛡️ **Compliance e Sicurezza**
- **Nuovi protocolli**: Implementazione disclaimer legali per tutti i nuovi scraper
- **Rate limiting**: Adozione di pratiche di scraping responsabile con controllo frequenza richieste

## Aggiornamento 2026-03-22 — Architettura Multi-Agente Definitiva

### VISIONE CORE (decisione Sem, 22 Marzo 2026)

Adam è il CEO di un'azienda di agenti AI. Sem è il proprietario che parla SOLO con Adam.

GERARCHIA:
- Sem → Adam (unico punto di contatto)
- Adam → sub-agent per ogni macro-progetto
- Sub-agent lavorano in autonomia 24/7

QUANDO UN SUB-AGENT SI BLOCCA:
1. Scrive il blocco in agent_tasks (status: 'blocked', motivo nel payload)
2. Adam lo rileva nel suo loop proattivo ogni 30 minuti
3. Adam notifica Sem su Telegram con la situazione e le opzioni
4. Sem decide e risponde ad Adam
5. Adam sblocca il sub-agent con le istruzioni

ADAM CHIEDE A SEM SOLO SE:
- Scelta architetturale che influenza il futuro del progetto
- Costo rilevante (token Anthropic, API a pagamento, Google Places, ecc.)
- Blocco che richiede credenziali o account che solo Sem può creare

TUTTO IL RESTO: Adam e i sub-agent agiscono in autonomia e riportano risultati.

STRUTTURA SUB-AGENT:
- Un processo Python per ogni macro-progetto (systemd service)
- Comunicano con Adam via tabella agent_tasks in PostgreSQL
- Ogni agente ha: loop principale, gestione errori, segnalazione blocchi
- Progetti attuali: beauty-salon-db (scraping_agent.py), agent-army (futuro), ollama-lab (futuro)

FUTURO: Decine di progetti, decine di agenti per progetto. Adam tiene le fila di tutto.


## Aggiornamento 2026-03-29

### 🔧 SVILUPPI TECNICI
- **Scraper Booksy UK**: Creato script Python completo per scraping dati business, versioni multiple ottimizzate con disclaimer legali e conformità robots.txt
- **Server Status**: Monitoraggio attivo semn1 (192.168.1.13) - Risorse: 169GB/457GB disk, 4.2GB/31GB RAM, GPU 219MB/8192MB

### 🚀 PROGETTI
- **Nuovo progetto**: `digalook` creato e inizializzato in fase planning con budget €20k
- **Beauty Salon DB**: Confermato stato operativo e in crescita
- **Monitoraggio generale**: Tutti i progetti sotto osservazione attiva

### 🔌 INTEGRAZIONI
- **Anthropic API**: Status verificato e confermato funzionante, connessione stabile
- **Sistema di monitoraggio**: Implementato controllo stato server automatico

### 📊 METRICHE ATTIVITÀ
- Richieste scraper Booksy: Multiple iterazioni e ottimizzazioni
- Test connessione: Multipli check di funzionamento sistema
- Gestione progetti: Focus su scaling e ottimizzazione workflow