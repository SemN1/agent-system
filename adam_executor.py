#!/usr/bin/env python3
"""
Adam Executor
Modulo per esecuzione autonoma di comandi sul server
Integrato in adam.py
"""

import os
import subprocess
import json
import logging
from datetime import datetime

log = logging.getLogger('adam')

# ============================================================
# CLASSIFICAZIONE AZIONI
# ============================================================

# Azioni che richiedono conferma
REQUIRES_APPROVAL = [
    'delete', 'drop', 'truncate',     # cancellazione dati
    'rm -rf', 'rmdir',                 # cancellazione file
    'api_key', 'password', 'token',   # credenziali
    'pay', 'purchase', 'billing',     # pagamenti
    'claude api',                      # costi API
]

# Azioni sicure - eseguite in autonomia
SAFE_ACTIONS = [
    'git status', 'git log', 'git add', 'git commit', 'git push',
    'python3', 'pip3 install',
    'systemctl status', 'systemctl restart',
    'docker ps', 'docker logs',
    'ls', 'cat', 'grep', 'find',
    'psql', 'SELECT',
    'ollama list', 'ollama pull',
    'tail', 'head', 'wc',
]


def needs_approval(action: str) -> bool:
    """Determina se un'azione richiede approvazione"""
    action_lower = action.lower()
    return any(keyword in action_lower for keyword in REQUIRES_APPROVAL)


def is_safe_action(action: str) -> bool:
    """Verifica se un'azione è nella lista sicura"""
    action_lower = action.lower()
    return any(safe in action_lower for safe in SAFE_ACTIONS)


# ============================================================
# ESECUZIONE COMANDI
# ============================================================

def execute_command(command: str, timeout: int = 60) -> dict:
    """
    Esegue un comando shell sul server
    
    Returns:
        dict con stdout, stderr, returncode, success
    """
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd='/home/semn1'
        )
        return {
            'success': result.returncode == 0,
            'stdout': result.stdout[:2000],
            'stderr': result.stderr[:500],
            'returncode': result.returncode,
            'command': command
        }
    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'stdout': '',
            'stderr': f'Timeout dopo {timeout}s',
            'returncode': -1,
            'command': command
        }
    except Exception as e:
        return {
            'success': False,
            'stdout': '',
            'stderr': str(e),
            'returncode': -1,
            'command': command
        }


def execute_python_script(script_path: str, args: str = '') -> dict:
    """Esegue uno script Python"""
    command = f"python3 {script_path} {args}"
    return execute_command(command, timeout=300)


def execute_claude_code(prompt: str, working_dir: str = '/home/semn1/origin') -> dict:
    """
    Lancia Claude Code in modalità non-interattiva
    Usato per generazione codice autonoma
    """
    # Escape del prompt per shell
    escaped_prompt = prompt.replace('"', '\\"').replace('`', '\\`')
    
    command = f'cd {working_dir} && claude --print "{escaped_prompt}" 2>&1'
    
    result = execute_command(command, timeout=300)
    log.info(f"Claude Code eseguito: {prompt[:50]}")
    return result


# ============================================================
# AZIONI PREDEFINITE ADAM
# ============================================================

def run_scraper(scraper_name: str, country: str = '') -> dict:
    """Lancia uno scraper specifico"""
    scraper_path = f"/home/semn1/beauty-salon-db/scrapers/{scraper_name}.py"
    
    if not os.path.exists(scraper_path):
        # Prova il path vecchio
        scraper_path = f"/home/semn1/directory_progetto/scrapers/{scraper_name}.py"
    
    if not os.path.exists(scraper_path):
        return {'success': False, 'stderr': f'Scraper {scraper_name} non trovato'}
    
    args = country if country else ''
    command = f"nohup python3 -u {scraper_path} {args} >> /home/semn1/beauty-salon-db/logs/{scraper_name}_{country}.log 2>&1 &"
    
    result = execute_command(command)
    if result['success']:
        result['message'] = f"Scraper {scraper_name} avviato in background"
    return result


def get_db_stats() -> dict:
    """Ottieni statistiche database saloni"""
    command = """PGPASSWORD='SalonsDB_2026_Secure!' psql -U salon_admin -d salons_db -h localhost -t -c "
        SELECT paese, COUNT(*) as totale, COUNT(telefono) as con_tel,
        ROUND(100.0*COUNT(telefono)/COUNT(*),1) as pct_tel
        FROM salons GROUP BY paese ORDER BY totale DESC;" 2>&1"""
    return execute_command(command)


def push_to_github(repo_path: str, message: str) -> dict:
    """Push su GitHub"""
    command = f"cd {repo_path} && git add -A && git commit -m '{message}' --allow-empty && git push"
    return execute_command(command, timeout=60)


def check_running_scrapers() -> dict:
    """Verifica scraper in esecuzione"""
    command = "ps aux | grep -E 'scraper|website_scraper|treatwell|fresha' | grep -v grep"
    return execute_command(command)


def get_server_status() -> dict:
    """Status generale del server"""
    results = {}
    r = execute_command("df -h / | tail -1 | awk '{print $3\"/\"$2\" (\"$5\" used)\"}'")
    results['disk'] = r['stdout'].strip() if r['success'] else 'N/A'
    r = execute_command("free -h | grep Mem | awk '{print $3\"/\"$2\" used\"}'")
    results['ram'] = r['stdout'].strip() if r['success'] else 'N/A'
    r = execute_command("nvidia-smi --query-gpu=memory.used,memory.total,temperature.gpu --format=csv,noheader,nounits 2>/dev/null")
    results['gpu'] = r['stdout'].strip() if r['success'] else 'N/A'
    r = execute_command("systemctl is-active adam adam_api 2>/dev/null | paste - -")
    results['systemd'] = r['stdout'].strip() if r['success'] else 'N/A'
    r = execute_command("/usr/bin/docker ps --format '{{.Names}}: {{.Status}}' 2>/dev/null")
    results['docker'] = r['stdout'].strip() if r['success'] else 'N/A'
    return results

def detect_action_intent(message: str) -> dict:
    """
    Rileva se il messaggio richiede un'azione sul server
    
    Returns:
        dict con action_type, params, requires_approval
    """
    message_lower = message.lower()
    
    # Scraping
    if any(kw in message_lower for kw in ['lancia scraper', 'avvia scraper', 'fai scraping', 'scrapa']):
        country = ''
        for c in ['italia', 'spagna', 'uk', 'germania', 'francia', 'belgio', 'olanda']:
            if c in message_lower:
                country = c.capitalize()
                break
        return {
            'action_type': 'run_scraper',
            'params': {'country': country},
            'requires_approval': False
        }
    
    # Status server
    if any(kw in message_lower for kw in ['status server', 'stato server', 'risorse server']):
        return {
            'action_type': 'server_status',
            'params': {},
            'requires_approval': False
        }
    
    # DB stats
    if any(kw in message_lower for kw in ['stats db', 'statistiche db', 'quanti saloni']):
        return {
            'action_type': 'db_stats',
            'params': {},
            'requires_approval': False
        }
    
    # GitHub push
    if any(kw in message_lower for kw in ['pusha', 'push su git', 'salva su git']):
        return {
            'action_type': 'git_push',
            'params': {},
            'requires_approval': False
        }
    
    # Genera codice
    if any(kw in message_lower for kw in ['scrivi codice', 'crea script', 'genera script', 'scrivi uno scraper']):
        return {
            'action_type': 'generate_code',
            'params': {'prompt': message},
            'requires_approval': False
        }
    
    # Cancellazione (richiede approvazione)
    if any(kw in message_lower for kw in ['cancella', 'elimina', 'svuota', 'drop']):
        return {
            'action_type': 'delete',
            'params': {},
            'requires_approval': True
        }
    
    return {'action_type': None, 'params': {}, 'requires_approval': False}


def execute_action(action_intent: dict, original_message: str) -> str:
    """
    Esegue l'azione rilevata e ritorna la risposta
    """
    action_type = action_intent['action_type']
    params = action_intent['params']
    
    if action_type == 'server_status':
        stats = get_server_status()
        docker = stats.get('docker', 'N/A')
        return (
            f"📊 Status Server semn1\n"
            f"💾 Disco: {stats.get('disk', 'N/A')}\n"
            f"🧠 RAM: {stats.get('ram', 'N/A')}\n"
            f"🎮 GPU: {stats.get('gpu', 'N/A')}\n"
            f"Adam/API: {stats.get('systemd', 'N/A')}\n"
            f"Docker:\n{docker}"
        )
    
    elif action_type == 'db_stats':
        result = get_db_stats()
        if result['success']:
            return f"📊 **Database Saloni:**\n```\n{result['stdout']}\n```"
        return f"❌ Errore: {result['stderr']}"
    
    elif action_type == 'run_scraper':
        country = params.get('country', '')
        result = run_scraper('website_scraper', country)
        if result['success']:
            return f"✅ Scraper avviato per {country or 'tutti i paesi'}\nLog: /home/semn1/beauty-salon-db/logs/"
        return f"❌ Errore avvio scraper: {result['stderr']}"
    
    elif action_type == 'git_push':
        result = push_to_github('/home/semn1/origin', f'Auto-update {datetime.now().strftime("%Y-%m-%d %H:%M")}')
        if result['success']:
            return "✅ Push su GitHub completato"
        return f"❌ Errore push: {result['stderr']}"
    
    elif action_type == 'generate_code':
        result = execute_claude_code(original_message)
        if result['success']:
            return f"✅ Codice generato:\n{result['stdout'][:1500]}"
        return f"❌ Errore Claude Code: {result['stderr']}"
    
    return "❓ Azione non riconosciuta"
