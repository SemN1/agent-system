#!/usr/bin/env python3
"""
Adam API Server
Endpoint compatibile OpenAI per Open WebUI
Espone Adam come modello selezionabile
"""

import os
import sys
import json
import logging
from datetime import date
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse
import uvicorn

# Aggiungi path per importare adam
sys.path.insert(0, '/home/semn1/origin')

log = logging.getLogger('adam-api')
logging.basicConfig(level=logging.INFO, format='%(asctime)s [ADAM-API] %(message)s')

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Adam API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import funzioni da adam.py
try:
    from adam import (
        process_message, load_memory_levels, KB_CONTENT,
        ask_ollama, ask_claude, build_system, ADAM_SYSTEM
    )
    log.info("Modulo Adam importato")
except Exception as e:
    log.error(f"Errore import Adam: {e}")


@app.get("/v1/models")
async def list_models():
    """Lista modelli disponibili - compatibile OpenAI"""
    return {
        "object": "list",
        "data": [
            {
                "id": "adam",
                "object": "model",
                "created": 1710000000,
                "owned_by": "origin",
                "name": "Adam - Agente Segretario"
            }
        ]
    }


@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    """Endpoint chat - compatibile OpenAI"""
    body = await request.json()
    messages = body.get("messages", [])
    stream = body.get("stream", False)

    # Estrai ultimo messaggio utente
    user_message = ""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            user_message = msg.get("content", "")
            break

    if not user_message:
        return JSONResponse({"error": "No user message"}, status_code=400)

    # Genera session_id dalla data
    session_id = f"webui_{date.today().isoformat()}"

    log.info(f"Richiesta WebUI: {user_message[:50]}")

    # Usa process_message di Adam (con memoria completa)
    try:
        response_text = process_message(user_message, session_id)
    except Exception as e:
        log.error(f"Errore process_message: {e}")
        response_text = f"Errore: {e}"

    if stream:
        async def generate():
            # Simula streaming parola per parola
            words = response_text.split(' ')
            for i, word in enumerate(words):
                chunk = {
                    "id": "adam-1",
                    "object": "chat.completion.chunk",
                    "choices": [{
                        "delta": {"content": word + (' ' if i < len(words)-1 else '')},
                        "index": 0,
                        "finish_reason": None
                    }]
                }
                yield f"data: {json.dumps(chunk)}\n\n"
            # Chunk finale
            yield f"data: {json.dumps({'choices': [{'delta': {}, 'finish_reason': 'stop'}]})}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(generate(), media_type="text/event-stream")
    else:
        return {
            "id": "adam-1",
            "object": "chat.completion",
            "model": "adam",
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": response_text
                },
                "index": 0,
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": len(user_message.split()),
                "completion_tokens": len(response_text.split()),
                "total_tokens": len(user_message.split()) + len(response_text.split())
            }
        }


@app.get("/v1/openapi.json")
async def openapi_spec():
    """OpenAPI spec richiesta da Open WebUI"""
    return {
        "openapi": "3.0.0",
        "info": {"title": "Adam API", "version": "1.0.0"},
        "paths": {
            "/v1/chat/completions": {"post": {"operationId": "chat"}},
            "/v1/models": {"get": {"operationId": "models"}}
        }
    }


@app.options("/v1/openapi.json")
async def openapi_spec_options():
    return {}


@app.options("/v1/chat/completions")
async def chat_options():
    return {}


@app.get("/health")
async def health():
    return {"status": "ok", "agent": "adam"}


if __name__ == "__main__":
    # Carica memoria all'avvio
    import adam
    adam.KB_CONTENT = adam.load_memory_levels()
    log.info(f"Memoria caricata: {len(adam.KB_CONTENT)} caratteri")

    uvicorn.run(app, host="0.0.0.0", port=11435, log_level="info")
