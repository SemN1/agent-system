#!/usr/bin/env python3
"""
Adam - Agente Segretario
Processo principale con memoria persistente, Telegram e task management
Version: 1.0
"""

import os
import sys
import json
import asyncio
import logging
import subprocess
import psycopg2
import requests
import chromadb
from datetime import datetime, date
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv

load_dotenv('/home/semn1/origin/.env')

# ============================================================
# CONFIG
# ============================================================

TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = int(os.getenv('TELEGRAM_ALLOWED_USERS', '2560082'))
CLAUDE_API_KEY = os.getenv('CLAUDE_API_KEY')
OLLAMA_HOST = os.getenv('OLLAMA_HOST', 'http://localhost:11434')
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'qwen2.5:14b')
DB_CONN = os.getenv('POSTGRES_CONN_STRING', 
                     'postgresql://agent_system:1@localhost:5432/agent_hub')
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

# ============================================================
# DATABASE
# ============================================================

def get_db():
    return psycopg2.connect(DB_CONN)

def save_conversation(session_id: str, role: str, content: str, interface: str = 'telegram'):
    """Salva messaggio nella memoria conversazionale"""
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO adam_conversations (session_id, interface, role, content)
            VALUES (%s, %s, %s, %s)
        """, (session_id, interface, role, content))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        log.error(f"Errore salvataggio conversazione: {e}")

def save_memory(memory_type: str, title: str, content: str, 
                project_id: str = None, importance: int = 5):
    """Salva fatto importante nella memoria semantica"""
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO adam_memory (memory_type, title, content, project_id, importance)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT DO NOTHING
        """, (memory_type, title, content, project_id, importance))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        log.error(f"Errore salvataggio memoria: {e}")

def get_recent_context(session_id: str, limit: int = 10) -> List[Dict]:
    """Recupera contesto recente della sessione"""
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            SELECT role, content, created_at
            FROM adam_conversations
            WHERE session_id = %s
            ORDER BY created_at DESC
            LIMIT %s
        """, (session_id, limit))
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return [{"role": r[0], "content": r[1], "time": str(r[2])} 
                for r in reversed(rows)]
    except Exception as e:
        log.error(f"Errore recupero contesto: {e}")
        return []

def get_system_status() -> Dict:
    """Recupera stato sistema da PostgreSQL"""
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            SELECT project_id, project_name, status, current_phase, 
                   last_action, next_action, last_updated
            FROM project_status
            ORDER BY status, project_name
        """)
        projects = cur.fetchall()
        
        cur.execute("""
            SELECT COUNT(*) FROM agent_tasks 
            WHERE status = 'pending'
        """)
        pending_tasks = cur.fetchone()[0]
        
        cur.execute("""
            SELECT SUM(cost_eur) FROM cost_tracking
            WHERE date >= DATE_TRUNC('month', CURRENT_DATE)
              AND provider = 'claude'
        """)
        monthly_cost = cur.fetchone()[0] or 0
        
        cur.close()
        conn.close()
        
        return {
            "projects": projects,
            "pending_tasks": pending_tasks,
            "monthly_cost_eur": float(monthly_cost)
        }
    except Exception as e:
        log.error(f"Errore status: {e}")
        return {}

# ============================================================
# INTELLIGENZA
# ============================================================

def ask_ollama(prompt: str, system: str = None, context: List = None) -> str:
    """Chiama Ollama per risposte di routine"""
    messages = []
    
    if system:
        messages.append({"role": "system", "content": system})
    
    if context:
        for msg in context[-6:]:
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
    
    messages.append({"role": "user", "content": prompt})
    
    payload = {
        "model": OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
        "options": {"temperature": 0.7, "num_predict": 1024}
    }
    
    try:
        resp = requests.post(f"{OLLAMA_HOST}/api/chat", 
                           json=payload, timeout=120)
        resp.raise_for_status()
        return resp.json()["message"]["content"]
    except Exception as e:
        log.error(f"Errore Ollama: {e}")
        return None

def ask_claude(prompt: str, system: str = None, context: List = None) -> str:
    """Chiama Claude API per task complessi"""
    messages = []
    
    if context:
        for msg in context[-10:]:
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
    
    messages.append({"role": "user", "content": prompt})
    
    headers = {
        "x-api-key": CLAUDE_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    
    payload = {
        "model": "claude-sonnet-4-20250514",
        "messages": messages,
        "max_tokens": 2048
    }
    
    if system:
        payload["system"] = system
    
    try:
        resp = requests.post("https://api.anthropic.com/v1/messages",
                           headers=headers, json=payload, timeout=120)
        resp.raise_for_status()
        result = resp.json()
        return result["content"][0]["text"]
    except Exception as e:
        log.error(f"Errore Claude: {e}")
        return None

def needs_claude(message: str) -> bool:
    """Decide se il messaggio richiede Claude o basta Ollama"""
    complex_keywords = [
        'scrivi codice', 'crea script', 'genera', 'analizza',
        'architett', 'progett', 'debug', 'errore complesso',
        'strategia', 'decisione importante', 'refactor'
    ]
    message_lower = message.lower()
    return any(kw in message_lower for kw in complex_keywords)

# ============================================================
# SYSTEM PROMPT DI ADAM
# ============================================================

ADAM_SYSTEM = """Sei Adam, l'agente segretario di Sem (Simone).

IDENTITÀ:
- Sei il punto di controllo centrale del sistema Origin
- Hai memoria persistente - ricordi tutto quello che è stato detto e fatto
- Gestisci e coordini tutti i progetti sottostanti
- Il tuo obiettivo è fare in modo che Sem non debba fare nulla manualmente

PROGETTI ATTIVI:
- beauty-salon-db: database scraping saloni europei (611k+ saloni)
- ollama-lab: testing LLM e TTS locali
- crm-personale: CRM per trattative
- personal-rag: RAG su documenti personali

SERVER:
- semn1 / 192.168.1.13 / Ubuntu 24 / GTX 1080 8GB
- Stack: Docker, n8n, PostgreSQL, ChromaDB, Ollama, Telegram

REGOLE:
1. Rispondi sempre in italiano
2. Sii conciso ma completo
3. Se devi eseguire qualcosa sul server, dì cosa stai facendo
4. Per azioni critiche (spesa soldi, cancellazione dati) chiedi conferma
5. Salva sempre le decisioni importanti nella memoria
6. Aggiorna GitHub quando ci sono cambiamenti significativi"""

# ============================================================
# ELABORAZIONE MESSAGGI
# ============================================================

def process_message(user_message: str, session_id: str) -> str:
    """Elabora messaggio e genera risposta"""
    
    # Salva messaggio utente
    save_conversation(session_id, 'user', user_message)
    
    # Recupera contesto
    context = get_recent_context(session_id)
    
    # Comandi speciali
    if user_message.strip().lower() in ['/status', 'status']:
        return generate_status_response()
    
    if user_message.strip().lower().startswith('/task '):
        return create_task(user_message[6:])
    
    if user_message.strip().lower() in ['/recap', 'genera recap']:
        return generate_daily_recap()
    
    # Costruisce prompt con contesto sistema
    system_status = get_system_status()
    
    enriched_system = ADAM_SYSTEM + f"""

STATO ATTUALE SISTEMA:
- Progetti: {len(system_status.get('projects', []))} progetti registrati
- Task in coda: {system_status.get('pending_tasks', 0)}
- Costo Claude questo mese: €{system_status.get('monthly_cost_eur', 0):.2f}
"""
    
    # Sceglie modello
    if needs_claude(user_message):
        log.info(f"Usando Claude per: {user_message[:50]}")
        response = ask_claude(user_message, enriched_system, context)
    else:
        log.info(f"Usando Ollama per: {user_message[:50]}")
        response = ask_ollama(user_message, enriched_system, context)
    
    if not response:
        response = "❌ Errore nella generazione della risposta. Riprova."
    
    # Salva risposta
    save_conversation(session_id, 'assistant', response)
    
    # Estrai e salva memorie importanti in background
    extract_memories(user_message, response)
    
    return response

def generate_status_response() -> str:
    """Genera risposta status sistema"""
    status = get_system_status()
    projects = status.get('projects', [])
    
    emoji_map = {
        'active': '🟢', 'paused': '⏸️', 
        'error': '🔴', 'planning': '📋', 'completed': '✅'
    }
    
    msg = f"📊 *Sistema Origin*\n🕐 {datetime.now().strftime('%d/%m %H:%M')}\n\n"
    
    for p in projects:
        pid, pname, pstatus, phase = p[0], p[1], p[2], p[3]
        emoji = emoji_map.get(pstatus, '⚪')
        msg += f"{emoji} *{pname}*\n"
        if phase:
            msg += f"   ↳ {phase[:60]}\n"
    
    msg += f"\n📋 Task in coda: {status.get('pending_tasks', 0)}"
    msg += f"\n💰 Costo mese: €{status.get('monthly_cost_eur', 0):.2f}"
    
    return msg

def create_task(task_description: str) -> str:
    """Crea un task per un agente"""
    try:
        import uuid
        task_id = f"task_{uuid.uuid4().hex[:8]}"
        
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO agent_tasks (task_id, from_agent, to_agent, task_type, payload)
            VALUES (%s, 'adam', 'scraping', 'manual_task', %s)
        """, (task_id, json.dumps({"description": task_description})))
        conn.commit()
        cur.close()
        conn.close()
        
        return f"✅ Task creato: `{task_id}`\n📋 {task_description}"
    except Exception as e:
        return f"❌ Errore creazione task: {e}"

def extract_memories(user_msg: str, adam_response: str):
    """Estrae e salva memorie importanti dalla conversazione"""
    keywords = {
        'credential': ['password', 'token', 'api key', 'credenzial'],
        'decision': ['decidiamo', 'scegliamo', 'useremo', 'architettura'],
        'code': ['script', 'python', 'bash', 'sql', 'json'],
    }
    
    combined = (user_msg + " " + adam_response).lower()
    
    for mem_type, kws in keywords.items():
        if any(kw in combined for kw in kws):
            save_memory(
                memory_type=mem_type,
                title=user_msg[:100],
                content=f"User: {user_msg}\nAdam: {adam_response[:500]}",
                importance=7
            )
            break

# ============================================================
# BACKUP NOTTURNO
# ============================================================

def generate_daily_recap() -> str:
    """Genera recap giornaliero e lo pusha su GitHub"""
    today = date.today().isoformat()
    
    try:
        conn = get_db()
        cur = conn.cursor()
        
        # Conversazioni di oggi
        cur.execute("""
            SELECT role, content, created_at
            FROM adam_conversations
            WHERE DATE(created_at) = CURRENT_DATE
            ORDER BY created_at
        """)
        conversations = cur.fetchall()
        
        # Memorie salvate oggi
        cur.execute("""
            SELECT memory_type, title, content
            FROM adam_memory
            WHERE DATE(created_at) = CURRENT_DATE
            ORDER BY importance DESC
        """)
        memories = cur.fetchall()
        
        # Task completati oggi
        cur.execute("""
            SELECT task_id, task_type, status, result
            FROM agent_tasks
            WHERE DATE(created_at) = CURRENT_DATE
        """)
        tasks = cur.fetchall()
        
        cur.close()
        conn.close()
        
    except Exception as e:
        return f"❌ Errore generazione recap: {e}"
    
    # Chiedi a Claude di generare il recap
    conv_text = "\n".join([f"{r[0]}: {r[1][:200]}" for r in conversations[-20:]])
    mem_text = "\n".join([f"[{m[0]}] {m[1]}" for m in memories])
    
    prompt = f"""Genera un recap giornaliero strutturato in markdown per il {today}.

Conversazioni di oggi (ultime 20):
{conv_text}

Memorie salvate:
{mem_text}

Task eseguiti: {len(tasks)}

Genera un file markdown con:
## Recap {today}
### Decisioni Prese
### Codici e Script
### Credenziali (solo nuove/modificate)
### Cambi Sistema
### Pending Tasks per Domani

Sii preciso e completo."""

    recap_content = ask_claude(prompt) or ask_ollama(prompt)
    
    if not recap_content:
        return "❌ Impossibile generare recap"
    
    # Salva su file
    recap_path = f"/home/semn1/origin/chat-history/{today}.md"
    os.makedirs("/home/semn1/origin/chat-history", exist_ok=True)
    
    with open(recap_path, 'w') as f:
        f.write(recap_content)
    
    # Push su GitHub
    try:
        subprocess.run(['git', '-C', '/home/semn1/origin', 'add', 'chat-history/'], 
                      check=True, capture_output=True)
        subprocess.run(['git', '-C', '/home/semn1/origin', 'commit', '-m', 
                       f'Daily recap {today}'], check=True, capture_output=True)
        subprocess.run(['git', '-C', '/home/semn1/origin', 'push'], 
                      check=True, capture_output=True)
        log.info(f"Recap {today} pushato su GitHub")
    except Exception as e:
        log.error(f"Errore push GitHub: {e}")
    
    return f"✅ Recap {today} generato e pushato su GitHub\n📁 `chat-history/{today}.md`"

# ============================================================
# TELEGRAM
# ============================================================

class TelegramBot:
    def __init__(self):
        self.api = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
        self.offset = 0
    
    def send(self, text: str, chat_id: int = None):
        chat_id = chat_id or TELEGRAM_CHAT_ID
        try:
            requests.post(f"{self.api}/sendMessage", json={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "Markdown"
            }, timeout=15)
        except Exception as e:
            log.error(f"Errore invio Telegram: {e}")
    
    def get_updates(self):
        try:
            resp = requests.get(f"{self.api}/getUpdates", 
                              params={"offset": self.offset, "timeout": 10},
                              timeout=15)
            resp.raise_for_status()
            return resp.json().get("result", [])
        except Exception as e:
            log.error(f"Errore getUpdates: {e}")
            return []
    
    def run(self):
        log.info("🤖 Adam avviato su Telegram")
        self.send("🤖 *Adam online*\nSono pronto. Cosa vuoi fare?")
        
        while True:
            updates = self.get_updates()
            
            for update in updates:
                self.offset = update["update_id"] + 1
                
                msg = update.get("message", {})
                if not msg:
                    continue
                
                user_id = msg.get("from", {}).get("id")
                if user_id != TELEGRAM_CHAT_ID:
                    continue
                
                text = msg.get("text", "").strip()
                if not text:
                    continue
                
                chat_id = msg["chat"]["id"]
                session_id = f"telegram_{date.today().isoformat()}"
                
                log.info(f"Messaggio ricevuto: {text[:50]}")
                
                # Genera risposta
                response = process_message(text, session_id)
                
                # Invia risposta
                self.send(response, chat_id)
            
            import time
            time.sleep(2)

# ============================================================
# CRON NOTTURNO
# ============================================================

def nightly_backup():
    """Eseguito dal cron alle 2:00 - backup completo"""
    log.info("Avvio backup notturno...")
    
    bot = TelegramBot()
    
    # 1. Genera recap giornaliero
    recap_result = generate_daily_recap()
    log.info(f"Recap: {recap_result}")
    
    # 2. Aggiorna snapshot sistema
    try:
        subprocess.run(['bash', '/home/semn1/origin/origin_backup.sh'], 
                      check=True, capture_output=True)
        log.info("Snapshot sistema aggiornato")
    except Exception as e:
        log.error(f"Errore snapshot: {e}")
    
    # 3. Notifica Telegram
    bot.send(f"✅ *Backup notturno completato*\n📅 {date.today().isoformat()}\n{recap_result}")
    
    log.info("Backup notturno completato")

# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--backup":
        nightly_backup()
    else:
        bot = TelegramBot()
        bot.run()
