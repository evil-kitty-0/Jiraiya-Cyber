# Jiraiya AI

**Jiraiya** is a local-first, privacy-focused AI assistant designed to run on Android/Termux with local LLM inference, persistent sessions, encrypted memory, web access, and a responsive web UI.

> **Project status:** Active development — stabilization/integration stage.

## What Jiraiya currently has

- Local LLM inference through `llama.cpp`
- General + coding model routing
- Python agent/orchestration layer
- Encrypted persistent memory
- Automatic memory classification
- Temporary 30-day memory cache
- Relevant-memory retrieval
- Persistent conversation sessions
- Conversation context handling
- Python HTTP API
- CORS for local UI/API separation
- Responsive web UI
- Web search integration
- Dedicated gold-price routing
- Calculator routing
- Coding/general assistant routing
- Experimental self-improvement subsystem

## Architecture

```text
Browser UI :3000
     │
     ▼
api/server.py :8090
     │
     ├── session_manager
     ├── session_context
     └── agent.py
           │
           ├── memory/*
           ├── web/web.py
           ├── calculator
           └── local LLM
                    │
                    ▼
             llama-server :8080
```

## Local models

| Role | Model | Context | Threads |
|---|---|---:|---:|
| General | Qwen3 0.6B Q4_K_M | 8192 | 6 |
| Coder | Qwen2.5 Coder 1.5B Q4 | 8192 | 6 |

Model files are intentionally **not committed** to this repository because GGUF files are large and local/private runtime assets.

## Privacy

Jiraiya is designed around local-first operation. Private runtime data and credentials must never be committed.

The repository `.gitignore` excludes:

- master keys
- `.env` files
- credentials
- encrypted/local memory databases
- session data
- logs and PID files
- local model files
- Python cache files

Before publishing or deploying any part of Jiraiya, inspect the repository for secrets.

## Current priorities

1. Stabilize the current UI and sessions.
2. Preserve reliable web/source verification.
3. Improve web performance without sacrificing factual reliability.
4. Improve memory behavior and context selection.
5. Finish knowledge upload/retrieval.
6. Add security/authentication where needed.
7. Add advanced tools, voice, PWA and plugin capabilities.
8. Revisit controlled autonomous self-improvement only after the foundation is stable.

## Important development rule

Do not replace deterministic/source-aware live-data processing with an LLM guess. For live information such as gold rates, sources should be collected and verified first; the local model should summarize verified information.

## Documentation

- **[ROADMAP.md](ROADMAP.md)** — complete project history, current status, decisions, known problems and future roadmap.

Future contributors and coding agents should read `ROADMAP.md` before making substantial changes, then inspect the actual source files before editing them.

## Development environment

Primary development environment:

- Android
- Termux
- Python
- `llama.cpp`
- Static HTML/CSS/JavaScript UI

The local development layout is expected to live under:

```text
~/jiraiya
```

## Status philosophy

Jiraiya is experimental software. Features marked as implemented in the roadmap have been tested at the project level during development, but this does not mean the system is production-ready.
