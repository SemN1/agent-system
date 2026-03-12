#!/bin/bash

# ============================================================
# AGENT SYSTEM - Setup Automatico
# Server: Ubuntu 24, GTX 1080 8GB VRAM
# Version: 2.0
# ============================================================

set -e  # Esci su qualsiasi errore

# Colori per output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_ok()   { echo -e "${GREEN}   ✅ $1${NC}"; }
log_warn() { echo -e "${YELLOW}   ⚠️  $1${NC}"; }
log_err()  { echo -e "${RED}   ❌ $1${NC}"; }
log_info() { echo -e "${BLUE}   ℹ️  $1${NC}"; }

echo ""
echo "=========================================="
echo "  AGENT SYSTEM - Setup Automatico v2.0"
echo "  Server: $(hostname) | $(date)"
echo "=========================================="
echo ""

# Verifica che siamo nella cartella giusta
if [ ! -f "docker-compose.yml" ] || [ ! -f ".env" ]; then
    log_err "Esegui setup.sh dalla stessa cartella di docker-compose.yml e .env"
    log_err "Cartella corrente: $(pwd)"
    exit 1
fi

# Carica variabili .env
source .env

# ============================================================
# STEP 1: Prerequisiti
# ============================================================
echo "--- STEP 1: Verifica prerequisiti ---"
echo ""

# Docker
if command -v docker &> /dev/null; then
    DOCKER_VERSION=$(docker --version | awk '{print $3}' | tr -d ',')
    log_ok "Docker installato (v$DOCKER_VERSION)"
else
    log_err "Docker non trovato!"
    echo "Installa con: curl -fsSL https://get.docker.com | sh"
    exit 1
fi

# Docker Compose
if docker compose version &> /dev/null; then
    COMPOSE_VERSION=$(docker compose version --short)
    log_ok "Docker Compose installato (v$COMPOSE_VERSION)"
else
    log_err "Docker Compose non trovato!"
    exit 1
fi

# GPU NVIDIA
if command -v nvidia-smi &> /dev/null; then
    GPU_NAME=$(nvidia-smi --query-gpu=name --format=csv,noheader,nounits 2>/dev/null | head -1)
    GPU_VRAM=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits 2>/dev/null | head -1)
    log_ok "GPU NVIDIA rilevata: $GPU_NAME ($GPU_VRAM MiB VRAM)"

    # Verifica NVIDIA Container Toolkit
    if docker run --rm --gpus all nvidia/cuda:11.0.3-base-ubuntu20.04 nvidia-smi &> /dev/null; then
        log_ok "NVIDIA Container Toolkit configurato"
    else
        log_warn "NVIDIA Container Toolkit non configurato - installo..."
        distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
        curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
        curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | \
            sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
            sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
        sudo apt-get update -q
        sudo apt-get install -y -q nvidia-container-toolkit
        sudo nvidia-ctk runtime configure --runtime=docker
        sudo systemctl restart docker
        log_ok "NVIDIA Container Toolkit installato"
    fi
else
    log_warn "GPU NVIDIA non rilevata - Ollama userà CPU (più lento)"
    log_info "Per GTX 1080: installa driver NVIDIA e nvidia-docker2"
fi

echo ""

# ============================================================
# STEP 2: Creazione directory
# ============================================================
echo "--- STEP 2: Creazione cartelle ---"
echo ""

sudo mkdir -p /data/{n8n,postgres,ollama,chromadb,pgadmin,shared}
sudo mkdir -p /data/shared/{scripts,logs,reports,workflows,backups}
sudo chown -R $USER:$USER /data
chmod 750 /data

log_ok "Struttura /data/ creata"
log_info "Cartelle: n8n, postgres, ollama, chromadb, pgadmin, shared"

echo ""

# ============================================================
# STEP 3: Copia script Python
# ============================================================
echo "--- STEP 3: Deploy script Python ---"
echo ""

SCRIPTS_SRC="$(pwd)"
SCRIPTS_DST="/data/shared/scripts"

for script in ollama_client.py claude_client.py chromadb_manager.py requirements.txt; do
    if [ -f "$SCRIPTS_SRC/$script" ]; then
        cp "$SCRIPTS_SRC/$script" "$SCRIPTS_DST/"
        log_ok "Copiato: $script"
    else
        log_warn "Non trovato: $script (skip)"
    fi
done

chmod +x $SCRIPTS_DST/*.py 2>/dev/null || true

echo ""

# ============================================================
# STEP 4: Avvio container Docker
# ============================================================
echo "--- STEP 4: Avvio container Docker ---"
echo ""

log_info "Download immagini Docker (prima volta: 5-10 minuti)..."
docker compose pull 2>&1 | grep -E 'Pulling|Pull complete|already' | while read line; do
    echo "   $line"
done

echo ""
log_info "Avvio container..."
docker compose up -d

echo ""
log_ok "Container avviati"

echo ""

# ============================================================
# STEP 5: Attesa container healthy
# ============================================================
echo "--- STEP 5: Attesa container pronti ---"
echo ""

log_info "Attendo che PostgreSQL sia pronto (max 60 secondi)..."
for i in $(seq 1 12); do
    if docker exec postgres pg_isready -U postgres &> /dev/null; then
        log_ok "PostgreSQL pronto (${i}0s)"
        break
    fi
    if [ $i -eq 12 ]; then
        log_err "PostgreSQL non risponde dopo 120s"
        log_err "Controlla: docker logs postgres"
        exit 1
    fi
    echo -n "."
    sleep 10
done

echo ""
log_info "Attendo che n8n sia pronto (max 90 secondi)..."
for i in $(seq 1 9); do
    if curl -sf http://localhost:5678/healthz &> /dev/null; then
        log_ok "n8n pronto (${i}0s)"
        break
    fi
    if [ $i -eq 9 ]; then
        log_warn "n8n non risponde ancora (potrebbe richiedere più tempo)"
    fi
    echo -n "."
    sleep 10
done

echo ""

# ============================================================
# STEP 6: Verifica database
# ============================================================
echo "--- STEP 6: Verifica database ---"
echo ""

sleep 5
if docker exec postgres psql -U postgres -d agent_hub -c "SELECT COUNT(*) FROM projects;" &> /dev/null; then
    PROJECT_COUNT=$(docker exec postgres psql -U postgres -d agent_hub -t -c "SELECT COUNT(*) FROM projects;" | tr -d ' ')
    log_ok "Database agent_hub OK ($PROJECT_COUNT progetti nel seed)"
else
    log_warn "Database non ancora pronto o init-db.sql non eseguito"
    log_info "Verifica manuale: docker exec -it postgres psql -U postgres"
fi

echo ""

# ============================================================
# STEP 7: Download modello Ollama
# ============================================================
echo "--- STEP 7: Download modello Ollama ---"
echo ""

MODEL=${OLLAMA_MODEL:-qwen2.5:7b}
log_info "Download modello: $MODEL"
log_info "Questa operazione può richiedere 5-15 minuti..."
log_warn "GTX 1080 (8GB VRAM): usando $MODEL (ottimizzato)"

# Attendi che Ollama sia pronto
for i in $(seq 1 6); do
    if curl -sf http://localhost:11434/api/tags &> /dev/null; then
        break
    fi
    echo -n "."
    sleep 10
done

docker exec ollama ollama pull $MODEL

log_ok "Modello $MODEL pronto"

echo ""

# ============================================================
# STEP 8: Installa dipendenze Python
# ============================================================
echo "--- STEP 8: Dipendenze Python ---"
echo ""

if command -v pip3 &> /dev/null; then
    log_info "Installazione dipendenze Python..."
    pip3 install -r /data/shared/scripts/requirements.txt -q --break-system-packages 2>/dev/null || \
    pip3 install -r /data/shared/scripts/requirements.txt -q
    log_ok "Dipendenze Python installate"
else
    log_warn "pip3 non trovato - installo..."
    sudo apt update -q && sudo apt install -y -q python3-pip
    pip3 install -r /data/shared/scripts/requirements.txt --break-system-packages
    log_ok "pip3 e dipendenze installate"
fi

echo ""

# ============================================================
# STEP 9: Test rapido
# ============================================================
echo "--- STEP 9: Test connessioni ---"
echo ""

# Test Ollama
if curl -sf http://localhost:11434/api/tags | grep -q "$MODEL" 2>/dev/null; then
    log_ok "Ollama risponde - modello $MODEL disponibile"
else
    log_warn "Ollama: verifica con 'curl http://localhost:11434/api/tags'"
fi

# Test ChromaDB
if curl -sf http://localhost:8000/api/v1/heartbeat &> /dev/null; then
    log_ok "ChromaDB risponde"
else
    log_warn "ChromaDB non risponde ancora (attendi 30s e riprova)"
fi

# Test PostgreSQL
if docker exec postgres psql -U postgres -d agent_hub -c "SELECT 1;" &> /dev/null; then
    log_ok "PostgreSQL agent_hub risponde"
fi

# Test n8n
if curl -sf http://localhost:5678/healthz &> /dev/null; then
    log_ok "n8n UI disponibile"
fi

echo ""

# ============================================================
# STEP 10: Crea script test
# ============================================================
echo "--- STEP 10: Script di test ---"
echo ""

cat > /data/shared/scripts/test_script.py << 'PYEOF'
#!/usr/bin/env python3
"""Test Script - Verifica integrazione con n8n"""
import sys
import json
from datetime import datetime

def main():
    result = {
        "status": "success",
        "timestamp": datetime.now().isoformat(),
        "message": "Agent System - Test script OK!",
        "hostname": __import__('socket').gethostname(),
        "args": sys.argv[1:] if len(sys.argv) > 1 else []
    }
    print(json.dumps(result, indent=2))
    return 0

if __name__ == "__main__":
    sys.exit(main())
PYEOF

chmod +x /data/shared/scripts/test_script.py
log_ok "Script di test creato"

echo ""

# ============================================================
# RIEPILOGO FINALE
# ============================================================
echo "=========================================="
echo -e "${GREEN}  ✅ SETUP COMPLETATO!${NC}"
echo "=========================================="
echo ""
echo "SERVIZI ATTIVI:"
docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || docker compose ps
echo ""
echo "ACCESSI:"
echo "  n8n UI:     http://localhost:5678"
echo "  n8n Login:  $N8N_USER / [vedi .env]"
echo "  pgAdmin:    http://localhost:5050 (se abilitato)"
echo "  Ollama:     http://localhost:11434"
echo "  ChromaDB:   http://localhost:8000"
echo ""
echo "PROSSIMI PASSI:"
echo "  1. Apri n8n: http://$(hostname -I | awk '{print $1}'):5678"
echo "  2. Importa workflow: workflow_daily_report.json"
echo "  3. Configura credenziali PostgreSQL in n8n"
echo "  4. Aggiungi Telegram token in .env quando pronto"
echo "  5. Torna dal Master Agent con l'output di questo script"
echo ""
echo "TEST MANUALE:"
echo "  python3 /data/shared/scripts/test_script.py"
echo "  docker exec -it postgres psql -U postgres -d agent_hub"
echo "  curl http://localhost:11434/api/tags"
echo ""
echo "=========================================="
echo ""

# Salva output in log
SETUP_LOG="/data/shared/logs/setup_$(date +%Y%m%d_%H%M%S).log"
mkdir -p /data/shared/logs
echo "Setup completato: $(date)" >> $SETUP_LOG
docker compose ps >> $SETUP_LOG
echo "Log salvato in: $SETUP_LOG"
