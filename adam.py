#!/usr/bin/env python3
"""
Adam - Agente Segretario
Processo principale con memoria persistente a tre livelli
Version: 2.0
"""

import os
import sys
import json
import logging
import subprocess
import hashlib
import psycopg2
import requests
import chromadb
from datetime import datetime, date
from typing import List
from dotenv import load_dotenv
from adam_executor import detect_action_intent, execute_action, needs_approval

load_dotenv('/home/semn1/origin/.env')

# ============================================================
# CONFIG
# ============================================================

TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = int(os.getenv('TELEGRAM_ALLOWED_USERS', '2560082'))
CLAUDE_API_KEY = os.getenv('CLAUDE_API_KEY')
OLLAMA_HOST = os.getenv('OLLAMA_HOST', 'http://localhost:11434')
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'qwen3:14b')
DB_CONN = os.getenv('POSTGRES_CONN_STRING',
                    'postgresql://agent_system:1@localhost:5432/agent_hub')
SALONS_DB_CONN = 'postgresql://salon_admin:SalonsDB_2026_Secure!@localhost:5432/salons_db'
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [ADAM] %(levelname)s %(message)s',
    handlers=[
        logging.FileHandler('/home/semn1/origin/adam.log'),
        logging.StreamHandler()
    ]
)
log = logging.getLogger('adam')

# Memoria globale
KB_CONTENT = ""

# ChromaDB
CHROMA_CLIENT = None
ADAM_COLLECTION = None

try:
    CHROMA_CLIENT = chromadb.HttpClient(host="localhost", port=8000)
    ADAM_COLLECTION = CHROMA_CLIENT.get_or_create_collection("adam_memory_vectors")
    log.info("ChromaDB connesso")
except Exception as e:
    log.warning(f"ChromaDB non disponibile: {e}")

# ============================================================
# DATABASE
# ============================================================

def get_db():
    return psycopg2.connect(DB_CONN)


def query_db_direct(sql, params=None):
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute(sql, params)
        cols = [d[0] for d in cur.description]
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return [dict(zip(cols, row)) for row in rows]
    except Exception as e:
        log.error(f"Errore query DB: {e}")
        return []


def save_conversation(session_id, role, content, interface='telegram'):
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO adam_conversations (session_id, interface, role, content) VALUES (%s, %s, %s, %s)",
            (session_id, interface, role, content)
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        log.error(f"Errore salvataggio conv: {e}")


def save_memory(memory_type, title, content, project_id=None, importance=5):
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO adam_memory (memory_type, title, content, project_id, importance) VALUES (%s, %s, %s, %s, %s)",
            (memory_type, title, content, project_id, importance)
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        log.error(f"Errore salvataggio memoria: {e}")


def get_recent_context(session_id, limit=10):
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            "SELECT role, content FROM adam_conversations WHERE session_id = %s ORDER BY created_at DESC LIMIT %s",
            (session_id, limit)
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return [{"role": r[0], "content": r[1]} for r in reversed(rows)]
    except Exception as e:
        log.error(f"Errore recupero contesto: {e}")
        return []


def get_system_status():
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT project_id, project_name, status, current_phase FROM project_status ORDER BY status, project_name")
        projects = cur.fetchall()
        cur.execute("SELECT COUNT(*) FROM agent_tasks WHERE status = 'pending'")
        pending = cur.fetchone()[0]
        cur.execute("SELECT COALESCE(SUM(cost_eur), 0) FROM cost_tracking WHERE date >= DATE_TRUNC('month', CURRENT_DATE) AND provider = 'claude'")
        cost = float(cur.fetchone()[0])
        cur.close()
        conn.close()
        return {"projects": projects, "pending_tasks": pending, "monthly_cost_eur": cost}
    except Exception as e:
        log.error(f"Errore status: {e}")
        return {"projects": [], "pending_tasks": 0, "monthly_cost_eur": 0}


def get_beauty_salon_stats():
    try:
        conn = psycopg2.connect(SALONS_DB_CONN)
        cur = conn.cursor()
        cur.execute("""
            SELECT paese, COUNT(*) as totale,
                   COUNT(telefono) as con_tel,
                   ROUND(100.0*COUNT(telefono)/COUNT(*),1) as pct_tel
            FROM salons GROUP BY paese ORDER BY totale DESC
        """)
        cols = [d[0] for d in cur.description]
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return [dict(zip(cols, row)) for row in rows]
    except Exception as e:
        log.error(f"Errore salons_db: {e}")
        return []

# ============================================================
# CHROMADB
# ============================================================

def search_archive(query, n_results=3):
    if not ADAM_COLLECTION:
        return ""
    try:
        results = ADAM_COLLECTION.query(query_texts=[query], n_results=n_results)
        if not results['documents'][0]:
            return ""
        found = "\n=== ARCHIVIO RILEVANTE ===\n"
        for doc in results['documents'][0]:
            found += f"- {doc[:300]}\n"
        return found
    except Exception as e:
        log.error(f"Errore ricerca archivio: {e}")
        return ""


def save_to_chroma(text, metadata=None):
    if not ADAM_COLLECTION:
        return
    try:
        doc_id = f"adam_{hashlib.md5(text.encode()).hexdigest()[:12]}"
        ADAM_COLLECTION.add(
            ids=[doc_id],
            documents=[text],
            metadatas=[metadata or {"date": date.today().isoformat()}]
        )
    except Exception as e:
        log.error(f"Errore ChromaDB: {e}")

# ============================================================
# MEMORIA A TRE LIVELLI
# ============================================================

def load_knowledge_base():
    url = "https://raw.githubusercontent.com/SemN1/origin/main/ADAM_KNOWLEDGE_BASE.md"
    try:
        resp = requests.get(url, headers={"Authorization": f"token {GITHUB_TOKEN}"}, timeout=15)
        resp.raise_for_status()
        log.info("KB caricata da GitHub")
        return resp.text
    except Exception as e:
        log.error(f"Errore KB GitHub: {e}")
        try:
            with open('/home/semn1/origin/ADAM_KNOWLEDGE_BASE.md', 'r') as f:
                log.info("KB caricata da file locale")
                return f.read()
        except Exception:
            return ""


def load_memory_levels():
    memory = ""

    kb = load_knowledge_base()
    if kb:
        memory += "=== KNOWLEDGE BASE FONDATIVA ===\n" + kb[:4000] + "\n\n"
        log.info(f"L1: {len(kb)} char")

    chat_dir = "/home/semn1/origin/chat-history"
    if os.path.exists(chat_dir):
        files = sorted([f for f in os.listdir(chat_dir) if f.endswith('.md')])[-7:]
        if files:
            memory += "=== RECAP ULTIMI 7 GIORNI ===\n"
            for fname in files:
                try:
                    with open(os.path.join(chat_dir, fname), 'r') as f:
                        memory += "\n--- " + fname + " ---\n" + f.read()[:1000] + "\n"
                except Exception:
                    pass
            log.info(f"L2: {len(files)} file")

    try:
        recent = query_db_direct(
            "SELECT role, content FROM adam_conversations WHERE created_at >= NOW() - INTERVAL '3 days' ORDER BY created_at DESC LIMIT 20"
        )
        if recent:
            memory += "\n=== CONVERSAZIONI RECENTI ===\n"
            for c in reversed(recent):
                memory += c['role'] + ": " + str(c['content'])[:200] + "\n"
            log.info(f"L2b: {len(recent)} conversazioni")
    except Exception as e:
        log.error(f"Errore L2b: {e}")

    return memory

# ============================================================
# INTELLIGENZA
# ============================================================

def ask_ollama(prompt, system=None, context=None):
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    if context:
        for msg in context[-6:]:
            messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": prompt})
    try:
        resp = requests.post(
            f"{OLLAMA_HOST}/api/chat",
            json={"model": OLLAMA_MODEL, "messages": messages, "stream": False,
                  "options": {"temperature": 0.7, "num_predict": 1024}},
            timeout=180
        )
        resp.raise_for_status()
        return resp.json()["message"]["content"]
    except Exception as e:
        log.error(f"Errore Ollama: {e}")
        return None


def ask_claude(prompt, system=None, context=None):
    messages = []
    if context:
        for msg in context[-10:]:
            messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": prompt})
    headers = {
        "x-api-key": CLAUDE_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    payload = {"model": "claude-sonnet-4-20250514", "messages": messages, "max_tokens": 2048}
    if system:
        payload["system"] = system
    try:
        resp = requests.post("https://api.anthropic.com/v1/messages",
                             headers=headers, json=payload, timeout=120)
        resp.raise_for_status()
        return resp.json()["content"][0]["text"]
    except Exception as e:
        log.error(f"Errore Claude: {e}")
        return None


def needs_claude(message):
    keywords = ['scrivi codice', 'crea script', 'genera', 'analizza',
                'architett', 'progett', 'debug', 'strategia', 'refactor',
                'beauty', 'salon', 'database', 'update', 'status']
    return any(kw in message.lower() for kw in keywords)

# ============================================================
# SYSTEM PROMPT
# ============================================================

ADAM_SYSTEM = """Sei Adam, l'agente segretario di Sem (Simone).

IDENTITA':
- Punto di controllo centrale del sistema Origin
- Hai memoria persistente - ricordi tutto
- Gestisci e coordini tutti i progetti
- Agisci in autonomia senza chiedere permessi per task di routine

PROGETTI:
- beauty-salon-db: 611k+ saloni europei, scraping attivo
- ollama-lab: testing LLM e TTS locali
- crm-personale: CRM trattative
- personal-rag: RAG documenti personali

SERVER: semn1 / 192.168.1.13 / Ubuntu 24 / GTX 1080 8GB
STACK: Docker, n8n, PostgreSQL, ChromaDB, Ollama, Telegram

REGOLE:
1. Rispondi sempre in italiano
2. Sii conciso ma completo
3. Agisci in autonomia, riporta risultati
4. Solo per azioni critiche chiedi conferma
5. Accedi direttamente al DB quando serve dati reali"""

# ============================================================
# ELABORAZIONE
# ============================================================

def build_system(user_message):
    status = get_system_status()

    projects_text = "\n\nPROGETTI ATTIVI:\n"
    for p in status.get('projects', []):
        projects_text += f"- {p[1]} ({p[0]}): {p[2]} - {p[3] or 'N/A'}\n"

    salon_text = ""
    salon_kw = ['salon', 'salone', 'beauty', 'scraping', 'database',
                'telefon', 'paese', 'italia', 'germania', 'francia', 'uk', 'spagna']
    if any(kw in user_message.lower() for kw in salon_kw):
        stats = get_beauty_salon_stats()
        if stats:
            salon_text = "\n\nDATI BEAUTY SALON DB:\n"
            for row in stats:
                salon_text += f"- {row['paese']}: {row['totale']:,} saloni, {row['pct_tel']}% tel\n"

    archive_text = search_archive(user_message)

    return (
        ADAM_SYSTEM
        + "\n\nKNOWLEDGE BASE:\n" + KB_CONTENT[:4000]
        + projects_text
        + salon_text
        + archive_text
        + "\n\nSISTEMA:\n"
        + f"- Task in coda: {status.get('pending_tasks', 0)}\n"
        + f"- Costo Claude mese: EUR {status.get('monthly_cost_eur', 0):.2f}\n"
    )


def process_message(user_message, session_id):
    save_conversation(session_id, 'user', user_message)
    context = get_recent_context(session_id)

    if user_message.strip().lower() in ['/status', 'status']:
        return generate_status_response()
    if user_message.strip().lower().startswith('/task '):
        return create_task(user_message[6:])
    if user_message.strip().lower() in ['/recap', 'genera recap']:
        return generate_daily_recap()

    system = build_system(user_message)

    if needs_claude(user_message):
        log.info(f"Usando Claude per: {user_message[:50]}")
        response = ask_claude(user_message, system, context)
    else:
        log.info(f"Usando Ollama per: {user_message[:50]}")
        response = ask_ollama(user_message, system, context)

    if not response:
        response = "Errore nella generazione della risposta. Riprova."

    # Rileva e esegui azioni autonome
    action_intent = detect_action_intent(user_message)
    if action_intent['action_type']:
        if action_intent['requires_approval']:
            response += f"\n\n⚠️ Quest'azione richiede la tua approvazione. Confermi? Rispondi /approva o /annulla"
        else:
            action_result = execute_action(action_intent, user_message)
            response += f"\n\n🔧 **Azione eseguita:**\n{action_result}"

    save_conversation(session_id, 'assistant', response)
    extract_memories(user_message, response)
    save_to_chroma(
        "User: " + user_message + "\nAdam: " + response[:500],
        {"date": date.today().isoformat(), "session_id": session_id}
    )
    return response


def extract_memories(user_msg, adam_response):
    keywords = {
        'credential': ['password', 'token', 'api key', 'credenzial'],
        'decision': ['decidiamo', 'scegliamo', 'useremo', 'architettura'],
        'code': ['script', 'python', 'bash', 'sql'],
    }
    combined = (user_msg + " " + adam_response).lower()
    for mem_type, kws in keywords.items():
        if any(kw in combined for kw in kws):
            save_memory(mem_type, user_msg[:100],
                        "User: " + user_msg + "\nAdam: " + adam_response[:500],
                        importance=7)
            break

# ============================================================
# COMANDI
# ============================================================

def generate_status_response():
    status = get_system_status()
    emoji_map = {'active': 'VERDE', 'paused': 'PAUSA', 'error': 'ERRORE',
                 'planning': 'PIANO', 'completed': 'FATTO'}
    msg = "Sistema Origin - " + datetime.now().strftime('%d/%m %H:%M') + "\n\n"
    for p in status.get('projects', []):
        emoji = emoji_map.get(p[2], '?')
        msg += f"[{emoji}] {p[1]}\n"
        if p[3]:
            msg += f"  {p[3][:60]}\n"
    msg += f"\nTask in coda: {status.get('pending_tasks', 0)}"
    msg += f"\nCosto mese: EUR {status.get('monthly_cost_eur', 0):.2f}"
    return msg


def create_task(task_description):
    try:
        import uuid
        task_id = f"task_{uuid.uuid4().hex[:8]}"
        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO agent_tasks (task_id, from_agent, to_agent, task_type, payload) VALUES (%s, 'adam', 'scraping', 'manual_task', %s)",
            (task_id, json.dumps({"description": task_description}))
        )
        conn.commit()
        cur.close()
        conn.close()
        return f"Task creato: {task_id}\n{task_description}"
    except Exception as e:
        return f"Errore: {e}"

# ============================================================
# BACKUP
# ============================================================

def generate_daily_recap():
    today = date.today().isoformat()
    try:
        conversations = query_db_direct(
            "SELECT role, content FROM adam_conversations WHERE DATE(created_at) = CURRENT_DATE ORDER BY created_at LIMIT 30"
        )
        memories = query_db_direct(
            "SELECT memory_type, title FROM adam_memory WHERE DATE(created_at) = CURRENT_DATE ORDER BY importance DESC LIMIT 20"
        )
    except Exception as e:
        return f"Errore: {e}"

    conv_text = "\n".join([c['role'] + ": " + str(c['content'])[:200] for c in conversations])
    mem_text = "\n".join(["[" + m['memory_type'] + "] " + m['title'] for m in memories])

    prompt = (
        "Genera recap giornaliero markdown per " + today + ".\n\n"
        "Conversazioni:\n" + conv_text + "\n\nMemorie:\n" + mem_text + "\n\n"
        "Struttura:\n## Recap " + today + "\n"
        "### Decisioni Prese\n### Codici e Script\n"
        "### Credenziali Nuove\n### Cambi Sistema\n### Pending Tasks Domani"
    )

    recap = ask_claude(prompt) or ask_ollama(prompt)
    if not recap:
        return "Impossibile generare recap"

    os.makedirs("/home/semn1/origin/chat-history", exist_ok=True)
    recap_path = "/home/semn1/origin/chat-history/" + today + ".md"
    with open(recap_path, 'w') as f:
        f.write(recap)

    try:
        subprocess.run(['git', '-C', '/home/semn1/origin', 'add', 'chat-history/'], capture_output=True)
        subprocess.run(['git', '-C', '/home/semn1/origin', 'commit', '-m', 'Daily recap ' + today], capture_output=True)
        subprocess.run(['git', '-C', '/home/semn1/origin', 'push'], capture_output=True)
        log.info("Recap " + today + " pushato su GitHub")
    except Exception as e:
        log.error(f"Errore push: {e}")

    return "Recap " + today + " generato e pushato su GitHub"


def update_knowledge_base():
    if date.today().weekday() != 6:
        return
    log.info("Aggiornamento settimanale KB...")
    memories = query_db_direct(
        "SELECT memory_type, title, content FROM adam_memory WHERE created_at >= NOW() - INTERVAL '7 days' ORDER BY importance DESC LIMIT 50"
    )
    if not memories:
        return
    mem_text = "\n".join(["[" + m['memory_type'] + "] " + m['title'] + ": " + str(m['content'])[:200] for m in memories])
    prompt = (
        "Aggiorna la Knowledge Base di Adam con le nuove informazioni della settimana.\n\n"
        "NUOVE MEMORIE:\n" + mem_text + "\n\n"
        "Genera SOLO la sezione da aggiungere in fondo alla KB:\n"
        "## Aggiornamento " + date.today().isoformat() + "\n"
        "Includi decisioni, credenziali nuove, cambi architetturali."
    )
    update_text = ask_claude(prompt) or ask_ollama(prompt)
    if update_text:
        with open('/home/semn1/origin/ADAM_KNOWLEDGE_BASE.md', 'a') as f:
            f.write("\n\n" + update_text)
        subprocess.run(['git', '-C', '/home/semn1/origin', 'add', 'ADAM_KNOWLEDGE_BASE.md'], capture_output=True)
        subprocess.run(['git', '-C', '/home/semn1/origin', 'commit', '-m', 'Weekly KB update ' + date.today().isoformat()], capture_output=True)
        subprocess.run(['git', '-C', '/home/semn1/origin', 'push'], capture_output=True)
        log.info("KB aggiornata e pushata")


def nightly_backup():
    log.info("Avvio backup notturno...")
    today = date.today().isoformat()
    bot = TelegramBot()
    results = []

    recap_result = generate_daily_recap()
    results.append("Recap: " + recap_result[:80])

    try:
        os.makedirs("/data/backups/secretary-chat", exist_ok=True)
        dump_path = "/data/backups/secretary-chat/db_" + today + ".sql.gz"
        subprocess.run(
            "PGPASSWORD='1' pg_dump -U agent_system -h localhost agent_hub | gzip > " + dump_path,
            shell=True, check=True
        )
        results.append("DB dump: " + dump_path)
    except Exception as e:
        results.append("DB dump fallito: " + str(e))

    try:
        update_knowledge_base()
        results.append("KB aggiornata")
    except Exception as e:
        log.error(f"Errore KB: {e}")

    subprocess.run("find /data/backups/secretary-chat -name '*.sql.gz' -mtime +90 -delete", shell=True)

    try:
        subprocess.run(['bash', '/home/semn1/origin/origin_backup.sh'], check=True, capture_output=True)
        results.append("Snapshot GitHub aggiornato")
    except Exception as e:
        log.error(f"Errore snapshot: {e}")

    bot.send("Backup notturno completato\n" + today + "\n\n" + "\n".join(results))
    log.info("Backup notturno completato")

# ============================================================
# TELEGRAM
# ============================================================

class TelegramBot:
    def __init__(self):
        self.api = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
        self.offset = 0

    def send(self, text, chat_id=None):
        chat_id = chat_id or TELEGRAM_CHAT_ID
        try:
            resp = requests.post(f"{self.api}/sendMessage", json={
                "chat_id": chat_id, "text": text, "parse_mode": "Markdown"
            }, timeout=15)
            log.info(f"Telegram send: {resp.status_code} - {text[:50]}")
        except Exception as e:
            log.error(f"Errore Telegram send: {e}")

    def get_updates(self):
        try:
            resp = requests.get(
                f"{self.api}/getUpdates",
                params={"offset": self.offset, "timeout": 10},
                timeout=15
            )
            resp.raise_for_status()
            return resp.json().get("result", [])
        except Exception as e:
            log.error(f"Errore getUpdates: {e}")
            return []

    def run(self):
        import time
        log.info("Adam avviato su Telegram")
        self.send("Adam online - Sono pronto. Cosa vuoi fare?")
        while True:
            updates = self.get_updates()
            for update in updates:
                self.offset = update["update_id"] + 1
                msg = update.get("message", {})
                if not msg:
                    continue
                if msg.get("from", {}).get("id") != TELEGRAM_CHAT_ID:
                    continue
                text = msg.get("text", "").strip()
                if not text:
                    continue
                chat_id = msg["chat"]["id"]
                session_id = "telegram_" + date.today().isoformat()
                log.info(f"Messaggio: {text[:50]}")
                response = process_message(text, session_id)
                self.send(response, chat_id)
            time.sleep(2)

# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    KB_CONTENT = load_memory_levels()
    log.info(f"Memoria caricata: {len(KB_CONTENT)} caratteri")

    if len(sys.argv) > 1 and sys.argv[1] == "--backup":
        nightly_backup()
    else:
        bot = TelegramBot()
        bot.run()
