#!/usr/bin/env bash
# Pull the local models into the Ollama volume. Run once after `make up`.
set -euo pipefail

FAST="${LLM_MODEL_FAST:-qwen2.5:3b-instruct}"
STRONG="${LLM_MODEL_STRONG:-qwen2.5:7b-instruct}"

docker compose exec ollama ollama pull "$FAST"
docker compose exec ollama ollama pull "$STRONG"
docker compose exec ollama ollama list
