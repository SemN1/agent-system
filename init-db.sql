-- ============================================================
-- AGENT SYSTEM - Database Initialization
-- Database: agent_hub
-- Version: 2.0
-- ============================================================

-- Crea utente e database dedicati
CREATE USER agent_system WITH PASSWORD 'agent_system_pwd_2026';
CREATE DATABASE agent_hub OWNER agent_system;
CREATE DATABASE n8n_db OWNER n8n_user;

-- Connettiti ad agent_hub per creare lo schema
\c agent_hub

-- Dai tutti i permessi ad agent_system
GRANT ALL PRIVILEGES ON DATABASE agent_hub TO agent_system;
GRANT ALL ON SCHEMA public TO agent_system;

-- ------------------------------------------------------------
-- TABELLA: projects
-- ------------------------------------------------------------
CREATE TABLE public.projects (
    id SERIAL PRIMARY KEY,
    project_id VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(50) NOT NULL,
    status VARCHAR(50) DEFAULT 'active',
    tenant_id VARCHAR(100),
    preferred_model VARCHAR(100) DEFAULT 'ollama:qwen2.5:7b',
    allow_premium BOOLEAN DEFAULT FALSE,
    priority INTEGER DEFAULT 5,
    config JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_projects_status ON public.projects(status);
CREATE INDEX idx_projects_tenant ON public.projects(tenant_id);

-- ------------------------------------------------------------
-- TABELLA: workflows
-- ------------------------------------------------------------
CREATE TABLE public.workflows (
    id SERIAL PRIMARY KEY,
    workflow_id VARCHAR(100) UNIQUE NOT NULL,
    project_id VARCHAR(100) REFERENCES public.projects(project_id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    schedule VARCHAR(100),
    status VARCHAR(50) DEFAULT 'active',
    last_execution TIMESTAMP,
    last_status VARCHAR(50),
    execution_count INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_workflows_project ON public.workflows(project_id);
CREATE INDEX idx_workflows_status ON public.workflows(status);

-- ------------------------------------------------------------
-- TABELLA: execution_logs
-- ------------------------------------------------------------
CREATE TABLE public.execution_logs (
    id SERIAL PRIMARY KEY,
    execution_id VARCHAR(100) UNIQUE NOT NULL,
    workflow_id VARCHAR(100) REFERENCES public.workflows(workflow_id) ON DELETE SET NULL,
    project_id VARCHAR(100) REFERENCES public.projects(project_id) ON DELETE CASCADE,
    task_name VARCHAR(255),
    status VARCHAR(50),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    duration_seconds INTEGER,
    error_message TEXT,
    error_type VARCHAR(100),
    retry_count INTEGER DEFAULT 0,
    output_summary TEXT,
    logs_path VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_execution_logs_project ON public.execution_logs(project_id);
CREATE INDEX idx_execution_logs_status ON public.execution_logs(status);
CREATE INDEX idx_execution_logs_date ON public.execution_logs(started_at DESC);
CREATE INDEX idx_execution_logs_error_type ON public.execution_logs(error_type)
    WHERE error_type IS NOT NULL;

-- ------------------------------------------------------------
-- TABELLA: cost_tracking
-- ------------------------------------------------------------
CREATE TABLE public.cost_tracking (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    provider VARCHAR(50) NOT NULL,
    model VARCHAR(100),
    project_id VARCHAR(100) REFERENCES public.projects(project_id) ON DELETE SET NULL,
    input_tokens INTEGER,
    output_tokens INTEGER,
    cost_usd DECIMAL(10, 6),
    cost_eur DECIMAL(10, 6),
    task_type VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_cost_tracking_date ON public.cost_tracking(date DESC);
CREATE INDEX idx_cost_tracking_project ON public.cost_tracking(project_id);
CREATE INDEX idx_cost_tracking_provider ON public.cost_tracking(provider);

-- Vista aggregata mensile
CREATE VIEW public.monthly_costs AS
SELECT
    DATE_TRUNC('month', date) as month,
    provider,
    SUM(cost_eur) as total_cost_eur,
    SUM(input_tokens) as total_input_tokens,
    SUM(output_tokens) as total_output_tokens
FROM public.cost_tracking
GROUP BY DATE_TRUNC('month', date), provider
ORDER BY month DESC, provider;

-- ------------------------------------------------------------
-- TABELLA: telegram_commands
-- ------------------------------------------------------------
CREATE TABLE public.telegram_commands (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    username VARCHAR(100),
    command VARCHAR(255) NOT NULL,
    args TEXT,
    response_status VARCHAR(50),
    execution_time_ms INTEGER,
    error_message TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_telegram_commands_user ON public.telegram_commands(user_id);
CREATE INDEX idx_telegram_commands_timestamp ON public.telegram_commands(timestamp DESC);

-- ------------------------------------------------------------
-- TABELLA: known_errors
-- ------------------------------------------------------------
CREATE TABLE public.known_errors (
    id SERIAL PRIMARY KEY,
    error_signature TEXT NOT NULL UNIQUE,
    error_pattern TEXT,
    error_type VARCHAR(100),
    solution TEXT NOT NULL,
    solution_code TEXT,
    success_count INTEGER DEFAULT 0,
    last_seen TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_known_errors_type ON public.known_errors(error_type);

-- ------------------------------------------------------------
-- TABELLA: reports
-- ------------------------------------------------------------
CREATE TABLE public.reports (
    id SERIAL PRIMARY KEY,
    report_id VARCHAR(100) UNIQUE NOT NULL,
    project_id VARCHAR(100) REFERENCES public.projects(project_id) ON DELETE SET NULL,
    type VARCHAR(50) NOT NULL,
    title VARCHAR(255),
    content_summary TEXT,
    content_path VARCHAR(500),
    generated_by VARCHAR(50),
    generation_cost_eur DECIMAL(10, 6),
    sent_to VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_reports_project ON public.reports(project_id);
CREATE INDEX idx_reports_type ON public.reports(type);

-- ------------------------------------------------------------
-- TABELLA: system_events
-- ------------------------------------------------------------
CREATE TABLE public.system_events (
    id SERIAL PRIMARY KEY,
    event_type VARCHAR(100) NOT NULL,
    component VARCHAR(100),
    message TEXT,
    metadata JSONB,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_system_events_type ON public.system_events(event_type);
CREATE INDEX idx_system_events_timestamp ON public.system_events(timestamp DESC);

-- ------------------------------------------------------------
-- TRIGGER: Auto-update updated_at
-- ------------------------------------------------------------
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_projects_updated_at
    BEFORE UPDATE ON public.projects
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_known_errors_updated_at
    BEFORE UPDATE ON public.known_errors
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Permessi su tutte le tabelle
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO agent_system;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO agent_system;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO agent_system;

-- ------------------------------------------------------------
-- SEED DATA
-- ------------------------------------------------------------
INSERT INTO public.projects (project_id, name, type, status, preferred_model, allow_premium, priority, config)
VALUES (
    'demo_scraping_pg',
    'Demo Scraping PagineGialle',
    'scraping',
    'active',
    'ollama:qwen2.5:7b',
    FALSE,
    5,
    '{"source": "paginegialle.it", "category": "salons", "regions": ["IT"]}'::JSONB
);

INSERT INTO public.projects (project_id, name, type, status, preferred_model, allow_premium, priority, config)
VALUES (
    'system',
    'System - Monitoring e Reports',
    'system',
    'active',
    'ollama:qwen2.5:7b',
    TRUE,
    1,
    '{"description": "Progetto di sistema per monitoring, report e manutenzione"}'::JSONB
);

INSERT INTO public.workflows (workflow_id, project_id, name, schedule, status, description)
VALUES (
    'wf_daily_report_001',
    'system',
    'Daily Report Generator',
    '0 10 * * *',
    'active',
    'Genera e invia report giornaliero su Telegram alle 10:00'
);

INSERT INTO public.workflows (workflow_id, project_id, name, schedule, status, description)
VALUES (
    'wf_demo_scraping_pg_001',
    'demo_scraping_pg',
    'Scraping PagineGialle Notturno',
    '0 2 * * *',
    'paused',
    'Scraping notturno PagineGialle - in attesa configurazione script'
);

INSERT INTO public.system_events (event_type, component, message, metadata)
VALUES (
    'startup',
    'database',
    'Database agent_hub inizializzato con successo',
    '{"version": "2.0", "tables_created": 8}'::JSONB
);

-- Messaggio finale
DO $$
BEGIN
    RAISE NOTICE '============================================';
    RAISE NOTICE 'Database agent_hub inizializzato con successo!';
    RAISE NOTICE 'Tabelle create: 8';
    RAISE NOTICE 'Progetti seed: 2 (system, demo_scraping_pg)';
    RAISE NOTICE 'Workflow seed: 2';
    RAISE NOTICE '============================================';
END $$;

-- Crea anche utente n8n_user per il database n8n_db
\c postgres
CREATE USER n8n_user WITH PASSWORD 'CHANGE_THIS_n8n_db_password_2026!';
GRANT ALL PRIVILEGES ON DATABASE n8n_db TO n8n_user;
