# Local LLM (Ollama) setup (offline)

## 1) Install Ollama on the host (not inside Docker)

## 2) Download models while you have internet
Recommended:
- qwen2.5:7b-instruct

```bash
ollama pull qwen2.5:7b-instruct
```

Optional:
```bash
ollama pull llama3.1:8b-instruct
```

## 3) Verify Ollama is running
```bash
curl http://localhost:11434/api/tags
```

## 4) Configure app
In `.env`:
- OLLAMA_BASE_URL=http://host.docker.internal:11434
- MODEL_CHAT=qwen2.5:7b-instruct

> Linux note: `host.docker.internal` may not work. Use host IP or Docker host-gateway config.
