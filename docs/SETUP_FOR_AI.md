# Jiraiya AI — Setup & AI Handoff Guide

This document is written so that a future AI coding assistant can understand how to restore and continue Jiraiya on a new machine.

## 1. Project source

Repository: `evil-kitty-0/Jiraiya-AI`

Clone the repository, then work from the project root:

```bash
git clone git@github.com:evil-kitty-0/Jiraiya-AI.git
cd Jiraiya-AI
```

The repository contains source code, UI, API, memory logic, web logic, model configuration, and the experimental self-improvement subsystem.

## 2. Important rule: secrets and private runtime data are NOT in Git

Never expect these files to exist after cloning:

- `memory/master.key`
- `memory/*.db.enc`
- `sessions/sessions.json`
- `knowledge/*.db`
- `.env` files
- local `.gguf` model files
- runtime logs/PID files

They are intentionally excluded by `.gitignore`.

**Never commit, print, paste into chat, or upload the master key or other credentials.**

## 3. Restoring the master key

If moving an existing Jiraiya installation and its encrypted memory to a new machine, restore the ORIGINAL `memory/master.key` from a secure private backup into:

```text
<JIRAIYA_ROOT>/memory/master.key
```

The encrypted memory database and its master key are a pair. Do not generate a new key when the goal is to decrypt an existing encrypted memory database.

If there is no existing encrypted memory to restore, let Jiraiya's memory subsystem create/use its normal key according to its current implementation.

## 4. Restoring the GGUF model

GGUF model binaries are intentionally not stored in Git. Download the required model separately from its legitimate/official distribution source and place it under:

```text
<JIRAIYA_ROOT>/models/
```

The expected local configuration is described in:

```text
models/models.json
```

At the current development stage the configuration includes a general Qwen3 0.6B GGUF and a coding Qwen2.5 Coder 1.5B GGUF configuration. The exact model files must match the filenames configured in `models/models.json`.

Do not commit GGUF binaries to this repository.

## 5. Local runtime architecture

Current major components:

- `agent.py` — main routing/assistant logic
- `api/server.py` — HTTP API
- `api/session_context.py` — current-conversation context builder
- `sessions/session_manager.py` — chat/session persistence
- `memory/` — encrypted memory and automatic memory logic
- `knowledge/` — knowledge storage/logic
- `web/` — web search and related functionality
- `models/models.json` — model configuration
- `ui/` — browser UI
- `self_improvement/` — experimental self-improvement system; preserve it unless the user explicitly asks to remove it

## 6. Local services and ports

Typical local development setup:

- Jiraiya API: `127.0.0.1:8090`
- llama.cpp model server: `127.0.0.1:8080`
- static UI server: `127.0.0.1:3000`

The API talks to the local llama.cpp server. Do not assume a model server is available until its health/status has been checked.

## 7. Safe startup pattern

From the project root, the API can be started in the background using the project's normal process pattern. Avoid starting llama-server in the foreground when the user wants the terminal available for other commands.

Before debugging, check:

```bash
cd <JIRAIYA_ROOT>
python -m py_compile agent.py
curl -s http://127.0.0.1:8090/health
```

Use the actual project scripts/configuration rather than inventing new ports or filenames.

## 8. Git workflow

The repository's `main` branch is the source of truth for committed source/docs.

Normal workflow:

```bash
git status
git add .
git commit -m "Describe the change"
git push
```

Before committing, verify that secrets, encrypted private data, model binaries, logs, backups, and runtime files are not staged.

Never use `git push --force` unless the user explicitly understands and requests a history rewrite.

## 9. Important development behavior

Jiraiya currently uses manual/controlled development for feature changes. The experimental self-improvement system exists but should not be treated as an unrestricted autonomous deployment mechanism.

When modifying source files:

1. Inspect the current implementation first.
2. Preserve working behavior that is unrelated to the requested change.
3. Make the smallest safe change.
4. Run syntax/tests relevant to the changed component.
5. Check Git diff before committing.
6. Do not expose secrets or private memory in logs, responses, commits, or documentation.

## 10. Memory expectations

The intended memory design is:

- relevant important information can become long-term memory;
- uncertain/possibly useful information can remain in a 30-day cache;
- irrelevant information should be discarded;
- expired cache data should be removed;
- a compact semantic/index-like representation may remain where the implementation supports it;
- only relevant memories should be injected into the current model context;
- secrets must not be stored as ordinary memories.

Do not replace the existing encrypted memory system with an unencrypted plaintext store without explicit user approval.

## 11. UI/session expectations

A chat session represents a conversation rather than treating every message as a separate chat. Session history should remain associated with its session ID, and the UI should restore/open existing sessions correctly.

The UI must remain responsive on mobile and desktop. Do not solve mobile UI issues by breaking desktop layout.

## 12. Web/search reliability

For live or changing information, prioritize verified/reliable sources and preserve the existing gold-price/search verification behavior. Do not blindly feed large amounts of raw web pages to the small local model, especially when a concise source comparison or structured extraction is possible.

## 13. Handoff checklist for any future AI

When continuing this project, first read:

1. `README.md`
2. `ROADMAP.md`
3. `docs/ARCHITECTURE.md`
4. `docs/DEVELOPMENT.md`
5. this file: `docs/SETUP_FOR_AI.md`
6. the relevant source files before editing them

Then determine what is already implemented instead of rebuilding existing features.

If the work is being moved from another machine, ask for/restore private runtime assets only when actually required:

- original `memory/master.key` for existing encrypted memory;
- required GGUF model binaries in `models/`;
- any other explicitly documented private runtime state.

Never ask the user to put secrets into the public repository.
