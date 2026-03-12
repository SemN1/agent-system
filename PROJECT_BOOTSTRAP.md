# PROJECT_BOOTSTRAP.md
## Sistema Origin — Regole Globali per Nuovi Progetti
**Versione:** 1.0 | **Ultimo aggiornamento:** Marzo 2026
**Proprietario:** Sem | **Agente Segretario:** Adam (Origin)

---

## 1. IDENTITÀ DEL SISTEMA

Stai operando all'interno del sistema **Origin** — un network di agenti AI costruito da Sem su un server Ubuntu locale. Ogni agente ha una chat dedicata, un repo GitHub dedicato, e comunica con il resto del sistema tramite GitHub e PostgreSQL.

**Il tuo superiore è Adam** — l'agente segretario che vive nella chat Origin. Adam ha visibilità su tutti i progetti e risponde via Telegram. Tu sei responsabile del tuo progetto specifico, Adam coordina tutto.

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

### Stack Docker
```
n8n:        http://localhost:5678   (workflow automation)
PostgreSQL: localhost:5432          (database centrale)
ChromaDB:   localhost:8000          (vector store / RAG)
Ollama:     localhost:11434         (LLM locale, modello: qwen2.5:14b)
```

### Database
```
agent_hub  — database centrale Origin
            user: agent_system | password: 1
            tabelle: project_status, cost_tracking, execution_logs, workflows

salons_db  — Beauty Salon DB
            user: salon_admin | password: SalonsDB_2026_Secure!
```

### Credenziali
```
Claude API Key:     [vedi /home/semn1/origin/.env]
Telegram Token:     [vedi /home/semn1/origin/.env]
Telegram User ID:   2560082 (Sem)
GitHub Token:       [vedi /home/semn1/origin/.env]
GitHub Username:    SemN1
```

### Path Importanti
```
/home/semn1/origin/              ← repo Origin (Adam, infrastruttura)
/home/semn1/beauty-salon-db/     ← repo Beauty Salon DB
/home/semn1/directory_progetto/scrapers/  ← scraper Python
/data/shared/scripts/            ← script condivisi tra agenti
/data/backups/secretary-chat/    ← backup snapshot Origin
```

---

## 3. STRUTTURA REPO GITHUB

Ogni progetto ha il suo repo dedicato su GitHub (SemN1):

```
SemN1/origin             ← infrastruttura e Adam
SemN1/beauty-salon-db    ← Beauty Salon DB
SemN1/ollama-lab         ← Ollama Lab
SemN1/crm-personale      ← CRM Personale
SemN1/personal-rag       ← Personal RAG
```

### Struttura standard di ogni repo progetto
```
[nome-progetto]/
├── README.md            ← descrizione progetto
├── STATUS.md            ← stato corrente (aggiornato daily)
├── AGENTS.md            ← chi fa cosa in questo progetto
├── docs/                ← documentazione tecnica
├── scripts/             ← codice e script
└── logs/                ← log importanti
```

---

## 4. REGOLE DEL DAILY UPDATE

Ogni agente deve aggiornare il proprio `STATUS.md` ogni volta che fa progressi significativi, e comunque almeno una volta al giorno se il progetto è attivo.

### Formato standard STATUS.md
```markdown
# Status: [Nome Progetto]
**Aggiornato:** YYYY-MM-DD HH:MM

## Stato
[active | paused | error | planning | completed]

## Fase Corrente
[descrizione breve della fase]

## Ultimo Step Completato
[cosa è stato fatto]

## Prossimo Step
[cosa fare dopo]

## Blocchi
[eventuali problemi o dipendenze]

## Metriche
- [metrica chiave 1]: [valore]
- [metrica chiave 2]: [valore]
```

### Come pushare l'aggiornamento
```bash
cd /home/semn1/[nome-repo]
git add STATUS.md
git commit -m "Daily update $(date '+%Y-%m-%d')"
git push origin main
```

---

## 5. AUTOMAZIONI STANDARD

Ogni progetto attivo deve avere queste automazioni su n8n:

### 5.1 Daily Status Push
**Workflow:** `[progetto]_daily_status`
**Schedule:** `0 22 * * *` (ogni sera alle 22:00)
**Funzione:** Legge stato da PostgreSQL, aggiorna STATUS.md, pusha su GitHub

### 5.2 Error Alert
**Workflow:** `[progetto]_error_alert`
**Trigger:** Webhook su errore critico
**Funzione:** Notifica Telegram a Sem con dettagli errore

### 5.3 Weekly Report
**Workflow:** `[progetto]_weekly_report`
**Schedule:** `0 9 * * 1` (ogni lunedì alle 9:00)
**Funzione:** Genera report settimanale con Ollama, invia su Telegram

---

## 6. COMANDI TELEGRAM DISPONIBILI

Invia al bot **SemnMasterBot**:

```
/status                    — overview tutti i progetti
/status [project-id]       — dettaglio progetto specifico
/projects                  — lista progetti
/report                    — report giornaliero
/costs                     — costi Claude del mese
/help                      — lista comandi
```

Project ID disponibili:
- `beauty-salon-db`
- `ollama-lab`
- `crm-personale`
- `personal-rag`

---

## 7. AGGIUNGERE UN NUOVO PROGETTO

Quando Sem apre una nuova chat di progetto, l'agente deve:

**1. Creare il repo GitHub**
```bash
# Su semn1
mkdir -p /home/semn1/[nome-progetto]
cd /home/semn1/[nome-progetto]
git init
git remote add origin https://[GITHUB_TOKEN]@github.com/SemN1/[nome-progetto].git
```

**2. Creare STATUS.md iniziale e pushare**
```bash
# Crea README e STATUS
git add .
git commit -m "Init progetto [nome-progetto]"
git push -u origin main
```

**3. Registrare il progetto in PostgreSQL**
```sql
INSERT INTO public.project_status (
    project_id, project_name, status,
    current_phase, github_status_url, last_updated_by
) VALUES (
    '[project-id]',
    '[Nome Progetto]',
    'active',
    'Setup iniziale',
    'https://raw.githubusercontent.com/SemN1/[nome-progetto]/main/STATUS.md',
    'agent'
);
```

**4. Notificare Adam**
Aggiornare il file `origin_backup.sh` aggiungendo il nuovo progetto alla lista.

---

## 8. REGOLE GENERALI

1. **Mai perdere contesto** — aggiorna STATUS.md prima che la chat si esaurisca
2. **GitHub è la memoria** — tutto ciò che è importante va su GitHub
3. **Comandi separati** — mai due comandi nello stesso box di codice
4. **Backup prima di cambiamenti critici** — sempre
5. **Notifica Adam** — per decisioni architetturali importanti aggiorna project_status in PostgreSQL
6. **Budget Claude** — limite €50/mese, alert a €40. Usa Ollama per task di routine
7. **Credenziali** — mai in chiaro nei commit, sempre in .env (già in .gitignore)

---

## 9. PROMPT DEL PROGETTO

*(Questa sezione viene compilata da Sem quando lancia un nuovo progetto)*

**Nome Progetto:** [DA COMPILARE]
**Project ID:** [DA COMPILARE]
**Obiettivo:** [DA COMPILARE]
**Agenti previsti:** [DA COMPILARE]
**Stack specifico:** [DA COMPILARE]
**Prima cosa da fare:** [DA COMPILARE]

---

*Questo file è mantenuto da Adam. Ultima versione sempre su:*
*https://github.com/SemN1/origin/blob/main/PROJECT_BOOTSTRAP.md*
