#!/usr/bin/env python3
"""
Claude API Client - Interface per Claude con cost tracking automatico
Version: 2.1 - Smart routing Haiku/Sonnet/Ollama
Usage:
    - Importa in altri script: from claude_client import ClaudeClient
    - Usa standalone: python claude_client.py --test
"""

import os
import sys
import json
import requests
import psycopg2
from typing import Dict, List, Optional, Any
from datetime import datetime, date
from decimal import Decimal


# ============================================================
# ROUTING STRATEGY
# ============================================================
# OLLAMA (gratis):
#   - monitoring, status, summarize log, categorizzazione,
#     estrazione dati, report giornalieri semplici, task ripetitivi
#
# HAIKU (economico ~$0.80/1M input):
#   - risposte bot Telegram semplici, classificazioni veloci,
#     task che richiedono qualità > Ollama ma non complessità
#
# SONNET (qualità alta ~$3/1M input):
#   - report strategici, email clienti, analisi complesse,
#     code generation, troubleshooting errori non noti
#
# OPUS: mai in automatico
# ============================================================

# Task type → modello consigliato
TASK_ROUTING = {
    # HAIKU
    "telegram_command":     "haiku",
    "classification":       "haiku",
    "quick_answer":         "haiku",
    "simple_extraction":    "haiku",
    # SONNET
    "strategic_report":     "sonnet",
    "weekly_report":        "sonnet",
    "monthly_report":       "sonnet",
    "email_generation":     "sonnet",
    "code_generation":      "sonnet",
    "code_refactoring":     "sonnet",
    "troubleshooting":      "sonnet",
    "architecture":         "sonnet",
    # DEFAULT
    "general":              "haiku",
}


class ClaudeClient:
    """Client per Claude API con cost tracking e smart routing integrati"""

    # Prezzi Claude (Marzo 2026)
    PRICING = {
        "claude-sonnet-4-6": {
            "input_per_mtok": 3.00,
            "output_per_mtok": 15.00
        },
        "claude-haiku-4-5-20251001": {
            "input_per_mtok": 0.80,
            "output_per_mtok": 4.00
        },
        "claude-opus-4-6": {
            "input_per_mtok": 15.00,
            "output_per_mtok": 75.00
        }
    }

    MODEL_ALIASES = {
        "sonnet": "claude-sonnet-4-6",
        "haiku":  "claude-haiku-4-5-20251001",
        "opus":   "claude-opus-4-6",
    }

    def __init__(
        self,
        api_key: str = None,
        model: str = None,
        max_tokens: int = 4096,
        temperature: float = 1.0,
        db_connection_string: str = None,
        project_id: str = None,
        usd_to_eur_rate: float = None
    ):
        self.api_key = api_key or os.getenv("CLAUDE_API_KEY")
        if not self.api_key:
            raise ValueError("CLAUDE_API_KEY non configurato")

        # Modello default: haiku (economico)
        raw_model = model or os.getenv("CLAUDE_MODEL", "haiku")
        self.model = self.MODEL_ALIASES.get(raw_model, raw_model)

        self.max_tokens = max_tokens
        self.temperature = temperature
        self.project_id = project_id

        self.db_conn_string = db_connection_string or os.getenv(
            "POSTGRES_CONN_STRING",
            "postgresql://agent_system:1@localhost:5432/agent_hub"
        )

        self.usd_to_eur = usd_to_eur_rate or float(os.getenv("USD_TO_EUR_RATE", "0.92"))
        self.base_url = "https://api.anthropic.com/v1"

    def _resolve_model(self, task_type: str, model_override: str = None) -> str:
        """Risolve il modello corretto in base al task_type"""
        if model_override:
            return self.MODEL_ALIASES.get(model_override, model_override)
        tier = TASK_ROUTING.get(task_type, "haiku")
        return self.MODEL_ALIASES[tier]

    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        task_type: str = "general",
        model_override: str = None,
        track_cost: bool = True
    ) -> Dict[str, Any]:
        """
        Genera risposta da prompt singolo con routing automatico.

        Args:
            prompt: Prompt utente
            system: System prompt
            max_tokens: Override max_tokens
            temperature: Override temperature
            task_type: Tipo task per routing e cost tracking
            model_override: Forza un modello specifico ('haiku', 'sonnet', 'opus')
            track_cost: Salva costo in DB
        """
        model = self._resolve_model(task_type, model_override)
        url = f"{self.base_url}/messages"

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }

        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens or self.max_tokens,
            "temperature": temperature if temperature is not None else self.temperature
        }

        if system:
            payload["system"] = system

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=120)
            response.raise_for_status()
            result = response.json()

            usage = result.get("usage", {})
            input_tokens = usage.get("input_tokens", 0)
            output_tokens = usage.get("output_tokens", 0)

            cost_usd, cost_eur = self._calculate_cost(input_tokens, output_tokens, model)

            if track_cost:
                self._save_cost_to_db(input_tokens, output_tokens, cost_usd, cost_eur, task_type, model)

            content = result.get("content", [])
            response_text = content[0].get("text", "") if content else ""

            return {
                "response": response_text,
                "usage": {
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens": input_tokens + output_tokens
                },
                "cost_usd": float(cost_usd),
                "cost_eur": float(cost_eur),
                "model": model
            }

        except requests.exceptions.RequestException as e:
            error_msg = str(e)
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_msg = f"{error_msg}: {e.response.json()}"
                except:
                    pass
            return {
                "error": error_msg,
                "response": "",
                "usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
                "cost_usd": 0.0,
                "cost_eur": 0.0
            }

    def chat(
        self,
        messages: List[Dict[str, str]],
        system: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        task_type: str = "general",
        model_override: str = None,
        track_cost: bool = True
    ) -> Dict[str, Any]:
        """Chat multi-turno con routing automatico"""
        model = self._resolve_model(task_type, model_override)
        url = f"{self.base_url}/messages"

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }

        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens or self.max_tokens,
            "temperature": temperature if temperature is not None else self.temperature
        }

        if system:
            payload["system"] = system

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=120)
            response.raise_for_status()
            result = response.json()

            usage = result.get("usage", {})
            input_tokens = usage.get("input_tokens", 0)
            output_tokens = usage.get("output_tokens", 0)

            cost_usd, cost_eur = self._calculate_cost(input_tokens, output_tokens, model)

            if track_cost:
                self._save_cost_to_db(input_tokens, output_tokens, cost_usd, cost_eur, task_type, model)

            content = result.get("content", [])
            response_text = content[0].get("text", "") if content else ""

            return {
                "response": response_text,
                "usage": {
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens": input_tokens + output_tokens
                },
                "cost_usd": float(cost_usd),
                "cost_eur": float(cost_eur),
                "model": model
            }

        except requests.exceptions.RequestException as e:
            return {
                "error": str(e),
                "response": "",
                "usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
                "cost_usd": 0.0,
                "cost_eur": 0.0
            }

    def generate_strategic_report(
        self,
        data: Dict[str, Any],
        report_type: str = "weekly",
        include_recommendations: bool = True
    ) -> str:
        """Genera report strategico — usa Sonnet"""
        system = (
            "Sei un consulente strategico esperto. Analizza dati di business e genera "
            "report esecutivi chiari, con insight actionable e raccomandazioni concrete. "
            "Usa Markdown professionale con sezioni ben strutturate."
        )

        prompt = f"""Genera un report {report_type} strategico basato su questi dati:

```json
{json.dumps(data, indent=2, ensure_ascii=False)}
```

Struttura richiesta:
1. Executive Summary (3-4 righe chiave)
2. Analisi Metriche Principali
3. Trend e Pattern Identificati
4. {'Raccomandazioni Strategiche' if include_recommendations else 'Conclusioni'}

Tono: Professionale ma chiaro."""

        result = self.generate(
            prompt, system=system,
            max_tokens=2000, temperature=0.7,
            task_type="strategic_report"
        )
        return result.get("response", "Errore: impossibile generare report")

    def draft_email(
        self,
        context: str,
        recipient_type: str = "client",
        tone: str = "professional",
        language: str = "it"
    ) -> Dict[str, str]:
        """Genera bozza email — usa Sonnet"""
        system = (
            f"Sei un assistente che scrive email {tone} in {language}. "
            "Genera oggetto e corpo email. Rispondi in formato JSON."
        )

        prompt = f"""Scrivi un'email per {recipient_type} basata su questo contesto:

{context}

Rispondi in JSON:
```json
{{
  "subject": "...",
  "body": "..."
}}
```"""

        result = self.generate(
            prompt, system=system,
            max_tokens=800, temperature=0.8,
            task_type="email_generation"
        )

        try:
            text = result.get("response", "{}").replace("```json", "").replace("```", "").strip()
            email = json.loads(text)
            return {"subject": email.get("subject", ""), "body": email.get("body", "")}
        except json.JSONDecodeError:
            return {"subject": "Errore", "body": result.get("response", "")}

    def refactor_code(
        self,
        code: str,
        language: str = "python",
        improvements: List[str] = None
    ) -> Dict[str, str]:
        """Refactoring codice — usa Sonnet"""
        if improvements is None:
            improvements = ["readability", "performance", "error_handling"]

        system = (
            f"Sei un senior {language} developer. Refactora il codice migliorando: "
            f"{', '.join(improvements)}. Rispondi in JSON."
        )

        prompt = f"""Refactora questo codice {language}:

```{language}
{code}
```

Rispondi in JSON:
```json
{{
  "refactored_code": "...",
  "changes_summary": "..."
}}
```"""

        result = self.generate(
            prompt, system=system,
            max_tokens=3000, temperature=0.3,
            task_type="code_refactoring"
        )

        try:
            text = result.get("response", "{}").replace("```json", "").replace("```", "").strip()
            refactored = json.loads(text)
            return {
                "refactored_code": refactored.get("refactored_code", code),
                "changes_summary": refactored.get("changes_summary", "")
            }
        except json.JSONDecodeError:
            return {"refactored_code": code, "changes_summary": "Errore parsing"}

    def troubleshoot_error(
        self,
        error_message: str,
        context: str = "",
        include_solution: bool = True
    ) -> Dict[str, Any]:
        """Analizza errore — usa Sonnet"""
        system = (
            "Sei un expert troubleshooter. Analizza errori tecnici, identifica root cause "
            "e proponi soluzioni concrete. Rispondi in JSON."
        )

        prompt = f"""Analizza questo errore:

Errore: {error_message}
Contesto: {context[:1500] if context else 'N/A'}

Rispondi in JSON:
```json
{{
  "root_cause": "...",
  "solution": "...",
  "prevention": "..."
}}
```"""

        result = self.generate(
            prompt, system=system,
            max_tokens=1000, temperature=0.2,
            task_type="troubleshooting"
        )

        try:
            text = result.get("response", "{}").replace("```json", "").replace("```", "").strip()
            return json.loads(text)
        except json.JSONDecodeError:
            return {"root_cause": "Errore parsing", "solution": result.get("response", ""), "prevention": ""}

    def get_monthly_cost_summary(self) -> Dict[str, Any]:
        """Ottieni summary costi del mese corrente"""
        try:
            conn = psycopg2.connect(self.db_conn_string)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT
                    SUM(cost_eur) as total_cost,
                    COUNT(*) as total_calls,
                    SUM(input_tokens) as total_input_tokens,
                    SUM(output_tokens) as total_output_tokens
                FROM cost_tracking
                WHERE provider = 'claude'
                  AND date >= DATE_TRUNC('month', CURRENT_DATE);
            """)
            row = cursor.fetchone()
            total_cost = float(row[0]) if row[0] else 0.0
            total_calls = row[1] or 0
            total_input = row[2] or 0
            total_output = row[3] or 0

            cursor.execute("""
                SELECT task_type, model, SUM(cost_eur) as cost, COUNT(*) as calls
                FROM cost_tracking
                WHERE provider = 'claude'
                  AND date >= DATE_TRUNC('month', CURRENT_DATE)
                GROUP BY task_type, model
                ORDER BY cost DESC;
            """)
            breakdown = {}
            for row in cursor.fetchall():
                key = f"{row[0]} ({row[1]})"
                breakdown[key] = {"cost_eur": float(row[2]), "calls": row[3]}

            current_day = datetime.now().day
            projection = (total_cost / current_day) * 30 if current_day > 0 else 0

            cursor.close()
            conn.close()

            return {
                "total_cost_eur": total_cost,
                "total_calls": total_calls,
                "total_tokens": {"input": total_input, "output": total_output},
                "breakdown_by_task": breakdown,
                "monthly_projection_eur": projection,
                "budget_limit_eur": 50.0,
                "budget_used_pct": (total_cost / 50.0) * 100
            }

        except Exception as e:
            print(f"Errore query DB: {e}", file=sys.stderr)
            return {"error": str(e), "total_cost_eur": 0.0}

    def _calculate_cost(self, input_tokens: int, output_tokens: int, model: str = None) -> tuple:
        """Calcola costo in USD e EUR"""
        m = model or self.model
        pricing = self.PRICING.get(m, self.PRICING["claude-haiku-4-5-20251001"])

        cost_usd = (
            (input_tokens / 1_000_000) * pricing["input_per_mtok"] +
            (output_tokens / 1_000_000) * pricing["output_per_mtok"]
        )
        cost_eur = cost_usd * self.usd_to_eur
        return Decimal(str(cost_usd)), Decimal(str(cost_eur))

    def _save_cost_to_db(
        self,
        input_tokens: int,
        output_tokens: int,
        cost_usd: Decimal,
        cost_eur: Decimal,
        task_type: str,
        model: str = None
    ):
        """Salva costo nel database PostgreSQL"""
        try:
            conn = psycopg2.connect(self.db_conn_string)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO cost_tracking (
                    date, provider, model, project_id,
                    input_tokens, output_tokens, cost_usd, cost_eur, task_type
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
            """, (
                date.today(), "claude", model or self.model, self.project_id,
                input_tokens, output_tokens, cost_usd, cost_eur, task_type
            ))
            conn.commit()
            cursor.close()
            conn.close()
        except Exception as e:
            print(f"Errore salvataggio costo in DB: {e}", file=sys.stderr)


# ============================================================
# Funzioni Standalone
# ============================================================

def generate_strategic_report_standalone(data_json: str, report_type: str = "weekly") -> Dict[str, Any]:
    client = ClaudeClient()
    try:
        data = json.loads(data_json)
    except json.JSONDecodeError:
        return {"error": "Invalid JSON input", "report": ""}
    report = client.generate_strategic_report(data, report_type)
    return {"report": report, "report_type": report_type, "timestamp": datetime.now().isoformat()}


def draft_email_standalone(context: str, recipient_type: str = "client") -> Dict[str, Any]:
    client = ClaudeClient()
    email = client.draft_email(context, recipient_type)
    email["timestamp"] = datetime.now().isoformat()
    return email


# ============================================================
# CLI Interface
# ============================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Claude API Client CLI")
    parser.add_argument("--test", action="store_true", help="Test connessione API")
    parser.add_argument("--prompt", type=str, help="Invia prompt")
    parser.add_argument("--costs", action="store_true", help="Mostra costi mensili")
    parser.add_argument("--project-id", type=str, help="ID progetto")
    parser.add_argument("--model", type=str, help="Modello: haiku, sonnet, opus")
    parser.add_argument("--task", type=str, default="general", help="Task type per routing")

    args = parser.parse_args()

    try:
        client = ClaudeClient(project_id=args.project_id, model=args.model)
    except ValueError as e:
        print(f"❌ Errore: {e}", file=sys.stderr)
        sys.exit(1)

    if args.test:
        print("🧪 Test connessione Claude API...")
        result = client.generate("Rispondi con 'OK' se mi ricevi.", max_tokens=10, track_cost=False)
        if result.get("error"):
            print(f"❌ Errore: {result['error']}")
            sys.exit(1)
        print(f"✅ Connessione OK")
        print(f"   Modello: {result['model']}")
        print(f"   Risposta: {result['response']}")
        print(f"   Token: {result['usage']['total_tokens']}")
        sys.exit(0)

    elif args.costs:
        print("💰 Costi Claude - Mese Corrente\n")
        summary = client.get_monthly_cost_summary()
        if summary.get("error"):
            print(f"❌ Errore: {summary['error']}")
            sys.exit(1)
        print(f"Total Spesa:     €{summary['total_cost_eur']:.4f}")
        print(f"Chiamate Totali: {summary['total_calls']}")
        print(f"Token Input:     {summary['total_tokens']['input']:,}")
        print(f"Token Output:    {summary['total_tokens']['output']:,}")
        print(f"\nProiezione Fine Mese: €{summary['monthly_projection_eur']:.2f}")
        print(f"Budget Usato: {summary['budget_used_pct']:.1f}% di €{summary['budget_limit_eur']:.2f}")
        print("\nBreakdown per Task:")
        for k, v in summary['breakdown_by_task'].items():
            print(f"  - {k}: €{v['cost_eur']:.4f} ({v['calls']} calls)")
        sys.exit(0)

    elif args.prompt:
        print(f"💬 Invio prompt a Claude ({args.model or 'auto'})...")
        result = client.generate(args.prompt, task_type=args.task)
        if result.get("error"):
            print(f"❌ Errore: {result['error']}")
            sys.exit(1)
        print(f"\n{result['response']}\n")
        print(f"🤖 Modello: {result['model']}")
        print(f"💰 Costo: €{result['cost_eur']:.6f} | 📊 Token: {result['usage']['total_tokens']}")
        sys.exit(0)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
