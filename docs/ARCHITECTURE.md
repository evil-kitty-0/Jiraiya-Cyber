# Jiraiya AI — Architecture

## 1. High-level design

Jiraiya follows a local-first layered architecture:

```text
┌──────────────────────────────┐
│ Responsive Web UI            │
│ ui/index.html                │
│ ui/style.css                 │
│ ui/app.js                    │
└──────────────┬───────────────┘
               │ HTTP/JSON
               ▼
┌──────────────────────────────┐
│ Python API                   │
│ api/server.py :8090          │
└──────────────┬───────────────┘
               │
        ┌──────┴────────┐
        ▼               ▼
 sessions          agent.py
        │               │
        │       ┌───────┼────────┐
        │       ▼       ▼        ▼
        │    memory    web    calculator
        │       │       │
        │       │       └── search/page tools
        │       │
        │       └── relevant memory context
        │
        └── conversation history
                        │
                        ▼
                llama-server :8080
                        │
                 local GGUF models
```

## 2. UI layer

The UI is a static browser application. It is responsible for:

- rendering the conversation
- creating/loading/deleting/renaming sessions
- collecting user messages
- sending API requests
- displaying responses and errors
- mobile sidebar behavior

The UI should remain independent from the LLM implementation. It communicates through the API rather than importing Python modules.

## 3. API layer

`api/server.py` is the boundary between browser and backend.

Responsibilities:

- JSON request/response handling
- CORS
- session endpoints
- chat endpoint
- health endpoint
- assembling conversation context
- calling `agent.route_user_message()`
- persisting user and assistant messages

The API should not duplicate memory logic or LLM routing logic.

## 4. Session layer

`sessions/session_manager.py` owns conversation-session persistence.

A session contains:

- UUID
- title
- messages
- created timestamp
- updated timestamp

The API sends the recent session history into `api/session_context.py`, which creates a compact context for the agent.

## 5. Agent layer

`agent.py` is the orchestration layer.

The main public flow is:

```text
route_user_message()
        │
        ├── explicit memory handling
        ├── automatic memory processing
        ├── memory request handling
        ├── gold intent
        ├── calculator intent
        ├── coding intent
        ├── web intent
        └── general LLM response
```

`ask_model()` is the local LLM invocation path. Relevant memory is dynamically loaded through `memory/memory_context.py` before the user message is sent to the model.

## 6. Memory layer

The memory subsystem is intentionally separated from sessions.

### Sessions

Store the conversation history needed to reopen a chat.

### Long-term memory

Stores stable information that can be useful across sessions.

### Temporary cache

Stores uncertain/temporary information for approximately 30 days.

### Retrieval

Only relevant memories should be injected into the active model context. The entire memory database should never be dumped into every prompt.

### Security

Memory storage is encrypted and secrets should be filtered before persistence.

## 7. Web layer

`web/web.py` provides search and page-reading functionality.

The web layer should remain responsible for retrieving external information. The LLM should not be treated as the source of truth for live information.

For live-data workflows:

```text
Query
  ↓
Search
  ↓
Collect sources
  ↓
Verify/compare/extract
  ↓
LLM summarizes verified facts
```

Avoid this unsafe/slow pattern:

```text
Query → fetch many full pages → dump raw HTML/text into tiny LLM → trust output
```

## 8. Model layer

`llama.cpp` provides local inference.

Current model roles:

- `general` → Qwen3 0.6B Q4_K_M
- `coder` → Qwen2.5 Coder 1.5B Q4

The routing layer chooses the appropriate model/behavior according to the task.

## 9. Self-improvement layer

`self_improvement/` is experimental.

The desired future flow is:

```text
Inspect source
   ↓
Generate bounded plan
   ↓
Generate patch
   ↓
Backup
   ↓
Apply patch
   ↓
Run tests
   ↓
Accept or rollback
```

The system is intentionally not considered production-ready because the current small local model has produced malformed structured output during self-improvement experiments.

## 10. Data boundaries

The project should maintain clear boundaries:

- UI → API
- API → agent/session layers
- agent → tools/memory/model
- memory → encrypted private storage
- web → external sources
- model → reasoning/summarization, not authoritative live-data storage

This separation makes debugging, testing and future replacement of components easier.

## 11. Future architecture direction

Potential future additions:

- document/knowledge ingestion
- local vector/semantic indexing
- plugin/tool registry
- authentication and user isolation
- encrypted multi-user file storage
- admin controls
- voice interface
- PWA packaging
- stronger model routing
- controlled self-improvement

These should be added without breaking the existing layer boundaries.
