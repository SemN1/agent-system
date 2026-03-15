-- ============================================================
-- ADAM - Database Schema
-- Agent Hub: memoria persistente, task queue, conversazioni
-- ============================================================

-- Conversazioni con Sem (memoria persistente)
CREATE TABLE IF NOT EXISTS adam_conversations (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(100),
    interface VARCHAR(50), -- telegram, webui, cli
    role VARCHAR(20),       -- user, adam
    content TEXT NOT NULL,
    embedding_id VARCHAR(100), -- riferimento a ChromaDB
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_adam_conv_session ON adam_conversations(session_id);
CREATE INDEX IF NOT EXISTS idx_adam_conv_created ON adam_conversations(created_at DESC);

-- Memoria semantica (fatti importanti estratti dalle conversazioni)
CREATE TABLE IF NOT EXISTS adam_memory (
    id SERIAL PRIMARY KEY,
    memory_type VARCHAR(50), -- decision, credential, code, architecture, task
    title VARCHAR(255),
    content TEXT NOT NULL,
    project_id VARCHAR(100),
    importance INTEGER DEFAULT 5, -- 1-10
    embedding_id VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_adam_memory_type ON adam_memory(memory_type);
CREATE INDEX IF NOT EXISTS idx_adam_memory_project ON adam_memory(project_id);

-- Coda task tra Adam e agenti
CREATE TABLE IF NOT EXISTS agent_tasks (
    id SERIAL PRIMARY KEY,
    task_id VARCHAR(100) UNIQUE NOT NULL,
    from_agent VARCHAR(100) NOT NULL, -- adam, scraping, rag, tts
    to_agent VARCHAR(100) NOT NULL,
    task_type VARCHAR(100) NOT NULL,  -- run_scraper, generate_code, report, alert
    payload JSONB DEFAULT '{}',
    status VARCHAR(50) DEFAULT 'pending', -- pending, running, done, error, waiting_approval
    requires_approval BOOLEAN DEFAULT FALSE,
    approved_by VARCHAR(100),
    result JSONB,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON agent_tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_to_agent ON agent_tasks(to_agent);
CREATE INDEX IF NOT EXISTS idx_tasks_created ON agent_tasks(created_at DESC);

-- Registro agenti attivi
CREATE TABLE IF NOT EXISTS adam_agents (
    id SERIAL PRIMARY KEY,
    agent_id VARCHAR(100) UNIQUE NOT NULL,
    agent_name VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(50) DEFAULT 'active', -- active, paused, error
    script_path VARCHAR(500),
    last_heartbeat TIMESTAMP,
    last_task_at TIMESTAMP,
    total_tasks INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Seed agenti iniziali
INSERT INTO adam_agents (agent_id, agent_name, description, script_path) VALUES
('scraping', 'Beauty Salon Scraper', 'Scraping saloni da Treatwell, Fresha, PagineGialle, etc.', '/home/semn1/beauty-salon-db/scrapers/'),
('rag', 'Personal RAG', 'Indicizzazione e ricerca documenti personali', '/home/semn1/personal-rag/'),
('tts', 'Ollama Lab TTS', 'Testing modelli text-to-speech locali', '/home/semn1/ollama-lab/')
ON CONFLICT (agent_id) DO NOTHING;

-- Log sessioni giornaliere (per backup notturno)
CREATE TABLE IF NOT EXISTS adam_daily_log (
    id SERIAL PRIMARY KEY,
    log_date DATE NOT NULL,
    decisions TEXT,      -- decisioni prese
    code_written TEXT,   -- script/codice prodotto
    credentials TEXT,    -- credenziali nuove o modificate
    system_changes TEXT, -- cambi all'infrastruttura
    pending_tasks TEXT,  -- cosa fare domani
    pushed_to_github BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_daily_log_date ON adam_daily_log(log_date);
