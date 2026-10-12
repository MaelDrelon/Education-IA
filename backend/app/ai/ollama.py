"""Fournisseur local via Ollama (API native /api/chat).

Mêmes deux usages que pour Claude :
  - génération : sortie JSON contrainte par un schéma (paramètre `format`) ;
  - analyse : boucle d'appels d'outils (paramètre `tools`, résultats renvoyés en role="tool").
Les outils sont déclarés au format Anthropic dans le reste du code ; on les convertit ici.
"""
import json
from collections.abc import Callable
from typing import Any

import httpx

from ..config import settings


def _chat(messages: list[dict], **extra) -> dict:
    payload = {"model": settings.ollama_model, "messages": messages, "stream": False, **extra}
    try:
        r = httpx.post(f"{settings.ollama_url}/api/chat", json=payload, timeout=settings.ollama_timeout)
    except httpx.ConnectError:
        raise RuntimeError(f"Ollama injoignable sur {settings.ollama_url} (lancé ? `ollama serve`)")
    if r.status_code == 404:
        raise RuntimeError(f"Modèle « {settings.ollama_model} » absent : `ollama pull {settings.ollama_model}`")
    r.raise_for_status()
    return r.json()["message"]


def to_ollama_tools(tools: list[dict]) -> list[dict]:
    return [{"type": "function", "function": {
        "name": t["name"], "description": t.get("description", ""), "parameters": t["input_schema"]}}
        for t in tools]


def structured(system: str, prompt: str, schema: dict) -> dict:
    """Renvoie un objet JSON conforme à `schema`."""
    message = _chat(
        [{"role": "system", "content": system},
         {"role": "user", "content": prompt + "\n\nRéponds uniquement avec l'objet JSON demandé."}],
        format=schema, options={"temperature": 0.4},
    )
    return json.loads(message["content"])


def tool_loop(system: str, question: str, tools: list[dict],
              execute: Callable[[str, dict], Any], max_rounds: int) -> str | None:
    """Fait tourner la boucle outils ; `execute(nom, args)` exécute un outil et renvoie son résultat.

    Renvoie la réponse finale, ou None si le nombre d'étapes maximal est atteint.
    """
    messages = [{"role": "system", "content": system}, {"role": "user", "content": question}]
    ollama_tools = to_ollama_tools(tools)

    for _ in range(max_rounds):
        message = _chat(messages, tools=ollama_tools, options={"temperature": 0})
        calls = message.get("tool_calls") or []
        if not calls:
            return (message.get("content") or "").strip()

        messages.append({"role": "assistant", "content": message.get("content", ""), "tool_calls": calls})
        for call in calls:
            name = call["function"]["name"]
            args = call["function"].get("arguments") or {}
            if isinstance(args, str):  # certains modèles renvoient une chaîne JSON
                try:
                    args = json.loads(args)
                except json.JSONDecodeError:
                    args = {}
            output = execute(name, args)
            messages.append({"role": "tool", "tool_name": name,
                             "content": json.dumps(output, ensure_ascii=False, default=str)})
    return None
