# Jiraiya-AI Base Roadmap (Integrated into Jiraiya-Cyber)

> This is the preserved handoff/history from the original Jiraiya-AI base. It is retained as reference; Jiraiya-Cyber adds the authorization-first cyber layer and online inference routing around it.

# Jiraiya AI — Project Roadmap & Development History

> **Purpose of this document:** This file is the persistent handoff/context document for Jiraiya. Any future LLM (ChatGPT, Gemini, Claude, local models, coding agents, etc.) should read this document before modifying the project. It records what has been built, why decisions were made, what is currently working, what is intentionally unfinished, and what should happen next.

## 1. Project Identity

- **Project name:** Jiraiya (repository: `Jiraiya-AI`)
- **Repository:** `evil-kitty-0/Jiraiya-AI`
- **Primary environment:** Android + Termux
- **Project root:** `~/jiraiya`
- **Architecture goal:** local-first, privacy-focused, multi-model AI assistant with a web UI, persistent sessions, encrypted memory, web access, and future self-improvement capabilities.
- **Development philosophy:** build and test features manually and safely first; autonomous self-modification/deployment is experimental and is not currently trusted as the primary development mechanism.

---

## 2. Original Vision

Jiraiya was started as a locally hosted personal AI assistant rather than a simple chatbot. The long-term vision is:

1. A ChatGPT-like web interface usable on mobile and desktop.
2. Local LLM inference through `llama.cpp`.
3. Multiple local models selected according to task type.
4. Persistent conversation sessions.
5. Long-term encrypted memory.
6. Temporary memory/cache with automatic expiry.
7. Automatic memory extraction from conversations.
8. Retrieval of only relevant memories into the active context.
9. Web access for current information.
10. A knowledge-upload system for PDF/TXT/MD files.
11. Secure/private storage and an encrypted vault concept.
12. Persona modes such as Mentor, Friendly, and Strict.
13. Multilingual interaction.
14. Installable/PWA-style UI.
15. Future voice interaction.
16. Future plugin/tool architecture.
17. Future self-improvement and controlled source-code modification.

The immediate priority is **stability, UI, sessions/memory, and reliable web access** before attempting more autonomous behavior.

---

## 3. Development Timeline / What Has Been Done

### Phase 0 — Initial concept and experimentation

The project began as an attempt to create a personal AI assistant that could run locally on constrained hardware. Early experimentation included Termux, Python, local LLMs, GitHub, Render/Replit concepts, API-based models, and a custom Jiraiya persona.

The project evolved away from a purely API-dependent chatbot toward a local-first architecture.

### Phase 1 — Local LLM engine

A local `llama.cpp` setup was established.

Current binaries/models:

- `~/llama.cpp/build/bin/llama-server`
- llama-server API: `127.0.0.1:8080`
- Jiraiya Python API: `127.0.0.1:8090`

Configured models:

#### Coder model

- ID: `coder`
- Model: Qwen2.5 Coder 1.5B
- File: `qwen2.5-coder-1.5b-q4.gguf`
- Context: 8192
- Threads: 6
- Max tokens: 400 (higher for some coding routes)

#### General model

- ID: `general`
- Model: Qwen3 0.6B
- File: `qwen3-0.6b-q4_k_m.gguf`
- Context: 8192
- Threads: 6
- Max tokens: 400

`models/models.json` stores these model configurations.

The local server is normally started in the background through the project's agent/server logic rather than running `llama-server` in the foreground.

---

## 4. Core Agent / Routing Layer

The main orchestration file is:

`agent.py`

The routing layer currently supports several intent classes:

- direct memory commands
- automatic memory processing
- explicit memory requests
- gold-price/web-related intent
- calculator intent
- coding intent
- general web intent
- normal general assistant conversation

The key function is:

`route_user_message(text)`

It was changed so that it **returns the final response string** instead of printing/returning `None`. This was necessary because the API layer needs to receive the response and send it to the UI.

The routing flow now roughly follows:

1. Clean incoming text.
2. Handle explicit memory-save commands.
3. Run automatic memory processing.
4. Handle explicit memory requests.
5. Route gold queries.
6. Route calculator queries.
7. Route coding requests.
8. Route general web requests.
9. Otherwise use the general local model.

The model call path also injects relevant memory context dynamically from `memory/memory_context.py`.

---

## 5. Memory System

A major part of the project has already been implemented.

### Encrypted storage

`memory/memory.py` provides encrypted persistent storage.

Current design includes:

- AES-256-CBC encryption through OpenSSL.
- PBKDF2 with 200,000 iterations.
- Random salt.
- HMAC-SHA256 integrity protection.
- Secret/master material stored separately rather than in normal source files.
- JSON-based encrypted memory database.

### Memory categories/types

Memory records contain metadata such as:

- content
- category
- importance
- memory type
- created time
- last accessed time
- source session
- expiry information

### Long-term memory

Important, stable information can be retained permanently.

Examples that were tested:

- identity information
- user preferences
- project information

### Temporary cache

Potentially useful but uncertain/temporary information can be stored in a temporary cache.

Current TTL:

`30 days`

Expired cache records are removed automatically.

### Automatic memory extraction

`memory/auto_memory.py` and `memory/memory_analyzer.py` were added to decide what should be remembered.

The intended policy is:

- Important/stable information → long-term memory.
- Potentially useful but uncertain/temporary information → 30-day cache.
- Irrelevant information → discard.
- Secrets/credentials → do not store.

The analyzer includes rules for:

- secrets
- temporary information
- project information
- identity
- preferences
- future decisions

### Memory retrieval

`memory/memory_context.py` retrieves only relevant memories for the current user message rather than dumping the entire memory database into the model context.

The current agent dynamically loads this module to avoid package/import-name conflicts.

A direct test successfully demonstrated retrieval of a stored preference/fact such as a favorite programming language.

### Memory privacy requirement

Jiraiya must **not** accidentally persist:

- API keys
- passwords
- authentication tokens
- private credentials
- other secrets

Existing encrypted memory infrastructure should be reused rather than creating duplicate unencrypted stores.

### Future memory improvement

The planned 30-day cache behavior includes preserving a very small semantic/index-like record after expiry when appropriate, so Jiraiya can remember the gist without retaining the original temporary content. This compact-index behavior is a future refinement and should not be assumed to be fully implemented yet.

---

## 6. Conversation Sessions

A session system has been implemented in:

`sessions/session_manager.py`

Storage:

`sessions/sessions.json`

Features implemented:

- create session
- list sessions
- load session
- add user/assistant messages
- rename session
- delete session
- timestamps
- UUID session IDs
- updated-at sorting

The goal is that a chat remains **one continuous conversation/session**, rather than every individual message becoming a separate chat.

Test sessions were created during development to verify the API/session behavior.

---

## 7. Conversation Context

File:

`api/session_context.py`

The context builder:

- accepts current message + previous history
- keeps the latest 20 history items
- includes only user/assistant messages
- formats them as a compact current-conversation context
- passes the current user message separately

This fixes the earlier problem where Jiraiya could lose track of the current conversation context.

---

## 8. Python API Server

File:

`api/server.py`

The API server runs on:

`127.0.0.1:8090`

Implemented endpoints:

- `GET /health`
- `GET /api/sessions`
- `GET /api/sessions/{id}`
- `POST /api/sessions`
- `POST /api/chat`
- `PUT /api/sessions/{id}`
- `DELETE /api/sessions/{id}`

The API imports the project root explicitly so `agent.py` and other project modules can be found reliably.

### CORS

CORS was added because the static UI runs on port 3000 while the API runs on port 8090.

Allowed methods currently include:

- GET
- POST
- PUT
- DELETE
- OPTIONS

The API health check has successfully returned a healthy state including:

- `engine: true`
- `session_context: true`
- `session_manager: true`

---

## 9. Web UI

UI directory:

`ui/`

Main files include:

- `ui/index.html`
- `ui/style.css`
- `ui/app.js`

The UI is a ChatGPT-like responsive interface designed for both mobile and desktop.

Implemented/attempted UI functionality includes:

- sidebar
- New Chat
- chat history/session list
- current conversation view
- message sending
- suggestions
- session restoration
- rename/delete session support
- mobile sidebar toggle
- connection to the Python API

The UI is served locally with:

`python -m http.server 3000 --directory ui`

and accessed at:

`http://127.0.0.1:3000`

### Known UI issue

The mobile sidebar close behavior has been identified as an area needing improvement. The current UI can toggle/open the sidebar in some flows, but a robust outside-tap/backdrop close behavior still needs to be verified and polished.

The desired final UI is:

- clean
- premium/modern
- responsive
- mobile-first without sacrificing desktop usability
- visually inspired by modern AI assistants, but not a direct copy of another product

---

## 10. Web Search System

Web module:

`web/web.py`

It provides search functionality and page-reading functionality.

The search layer can return multiple search results and was successfully tested with queries such as:

`latest gold price India`

Search providers/results have worked sufficiently to return real search-result titles and URLs.

### Important recent regression and rollback

A recent experimental change modified `ask_web()` to fetch the contents of multiple result pages using `read_page()` and pass those contents to the small local model.

Problems discovered:

1. It became extremely slow on the Android/Termux environment (one test took about 81 seconds).
2. The model produced a gold-price answer that was not considered reliably verified.
3. This disturbed the previously working web-answer/verification behavior.

The experimental change was therefore **rolled back**.

The relevant backup files created during debugging were:

- `agent.py.before_web_context_fix`
- `agent.py.before_fast_web_fix`

The original version was restored from:

`agent.py.before_web_context_fix`

and `agent.py` successfully passed `python -m py_compile agent.py` after restoration.

### Web-search design rule going forward

Do **not** blindly fetch multiple full webpages and feed raw page text into the tiny local model.

For current/live information such as gold prices, the system should prioritize:

1. reliable search results/snippets or structured sources
2. source comparison/verification
3. extraction of the actual value/date/source
4. concise answer
5. explicit uncertainty when sources disagree or are insufficient

Performance is important because the local hardware/model is constrained.

---

## 11. Gold Price Feature

Jiraiya has a dedicated gold-related intent route.

The goal is not merely to search the phrase "gold price" but to provide a useful, current and preferably verified Indian gold-rate answer.

The project previously had a gold summary/verification mechanism in the web layer, and it should be preserved rather than replaced with a generic LLM guess.

Future improvements should include:

- source prioritization
- date/time extraction
- purity-aware rates (for example 24K/22K where available)
- city/India scope handling
- conflict detection between sources
- no-answer/no-confidence behavior when sources are inadequate

The model should never invent a live rate.

---

## 12. Calculator

Jiraiya contains calculator routing and a calculator answer path.

A separate scientific calculator upgrade was considered, but that work was intentionally paused/closed for the time being so that the project could focus on deployment, UI, sessions, memory and web access.

Do not restart that larger calculator refactor unless explicitly requested.

---

## 13. Self-Improvement System

An experimental `self_improvement/` subsystem exists.

The long-term idea is for Jiraiya to inspect its own source, generate an improvement plan, make controlled modifications, run tests, and potentially improve itself.

However, this is **not currently the primary development path**.

A recent experiment with:

`improvement_engine.py`

failed because the small local model produced malformed JSON even after repair attempts.

Conclusion:

- autonomous self-modification is too unreliable on the current small model/hardware setup
- do not delete the experimental subsystem
- do not make it the next major milestone
- manually implement and test important features first
- revisit autonomous self-improvement when stronger hardware/models are available

Future self-improvement must include strict safeguards such as:

- backups
- syntax checks
- unit/integration tests
- bounded file access
- diff review
- rollback on failure
- no secret exposure
- no uncontrolled deployment

---

## 14. Current Runtime / Startup Reference

### Start llama.cpp server

The preferred project pattern is to start the model server through the agent/server logic in the background, for example using the project's server-start mechanism rather than running the server interactively in the foreground.

### Start API

```bash
cd ~/jiraiya
if [ -f api/server.pid ]; then kill "$(cat api/server.pid)" 2>/dev/null || true; fi
sleep 1
nohup python api/server.py > api/server.log 2>&1 &
echo $! > api/server.pid
sleep 2
curl -s http://127.0.0.1:8090/health
```

Expected healthy structure:

```json
{
  "ok": true,
  "service": "jiraiya-api",
  "engine": true,
  "session_context": true,
  "session_manager": true
}
```

### Start UI

```bash
cd ~/jiraiya
nohup python -m http.server 3000 --directory ui > ui/ui_server.log 2>&1 &
echo $! > ui/ui_server.pid
sleep 2
```

Then open:

`http://127.0.0.1:3000`

---

## 15. Important Debugging Lessons

### Do not assume function signatures

A previous bug happened because `agent.py` called:

`search_web(query, max_results=5)`

while `web/web.py` defines `search_web(query)` without a `max_results` argument.

This caused:

`search_web() got an unexpected keyword argument 'max_results'`

The call was corrected.

### Keep web retrieval separate from model reasoning

Search results, source verification, page retrieval and model summarization should be distinct stages. A tiny model should not be trusted to turn arbitrary live-web text into a fact without source-aware logic.

### Avoid unnecessary network work

Fetching five full webpages from Termux can be very slow. Performance must be treated as a first-class requirement.

### Always make backups before source replacement

During development, backups such as:

`agent.py.before_*`

have been useful for safe rollback.

### Termux `/tmp` limitation

In this environment, attempts to write to `/tmp` produced `Permission denied`. Project-local temporary files under `~/jiraiya` are writable and should be preferred.

### File replacement preference

When giving manual file replacement instructions for this project, include an explicit `rm` command before recreating/replacing the file. This is a project workflow preference.

---

## 16. Current Project Status — September 2026

### Working / implemented

- [x] Local llama.cpp inference
- [x] General local model
- [x] Coder local model
- [x] Model configuration file
- [x] Main agent routing
- [x] Memory save/retrieval
- [x] Encrypted memory storage
- [x] Automatic memory analysis
- [x] 30-day temporary memory cache concept
- [x] Secret filtering in memory logic
- [x] Relevant-memory context injection
- [x] Session manager
- [x] Conversation context builder
- [x] Python API server
- [x] Session REST endpoints
- [x] Chat REST endpoint
- [x] CORS
- [x] Static web UI
- [x] UI ↔ API communication
- [x] Web search module
- [x] Gold intent route
- [x] Calculator route
- [x] Coding route
- [x] Backup/rollback workflow

### Partially complete / needs verification

- [ ] Robust mobile sidebar close/outside-click behavior
- [ ] Final premium UI polish
- [ ] Fully reliable live-web verification
- [ ] Web search speed optimization without reducing factual reliability
- [ ] Better session title generation
- [ ] Better identity/current-user handling in prompts
- [ ] More rigorous integration tests

### Planned but not yet complete

- [ ] Knowledge upload (PDF/TXT/MD) integrated into retrieval
- [ ] Encrypted vault
- [ ] Plugin/tool system
- [ ] Persona modes
- [ ] Multilingual optimization
- [ ] PWA/installable experience
- [ ] Voice interaction
- [ ] Stronger long-term memory compaction/indexing
- [ ] User/account authentication if multi-user deployment is pursued
- [ ] End-to-end encrypted user file storage for a multi-user version
- [ ] Master-admin controls for a future multi-user deployment
- [ ] Safe autonomous self-improvement
- [ ] Production deployment

---

## 17. Recommended Next Development Order

Future LLMs/agents should follow this order unless the user explicitly changes priorities:

### Milestone A — Stabilize current system

1. Verify restored original web behavior.
2. Verify API health.
3. Verify UI chat.
4. Verify sessions across page reloads.
5. Fix mobile sidebar closing.
6. Confirm memory save/retrieval does not leak internal messages.

### Milestone B — Reliable web access

1. Inspect the original `web/web.py` verification logic.
2. Preserve working gold-summary behavior.
3. Improve source verification without full-page fetching by default.
4. Add source/date/conflict handling.
5. Benchmark response time on Termux.

### Milestone C — Production-quality UI

1. Mobile responsiveness.
2. Desktop responsiveness.
3. Sidebar animation/overlay.
4. Chat bubbles and code rendering.
5. Loading/typing state.
6. Error states.
7. Session management UX.
8. Clean settings area.

### Milestone D — Knowledge + memory expansion

1. Knowledge file upload.
2. Document extraction.
3. Local indexing/retrieval.
4. Better semantic memory retrieval.
5. Compact expired-memory index.

### Milestone E — Security/privacy

1. Secret isolation.
2. Strong file permissions.
3. Encryption audit.
4. Authentication if multi-user.
5. Access control.
6. Secure admin functions.
7. Backup/recovery design.

### Milestone F — Advanced capabilities

1. Plugins/tools.
2. Persona modes.
3. Voice.
4. PWA.
5. Better model routing.
6. Optional external APIs.

### Milestone G — Controlled self-improvement

Only after the above system is stable:

1. source inspection
2. plan generation
3. patch generation
4. automated tests
5. diff review
6. backup
7. safe application
8. rollback
9. human approval for risky changes

---

## 18. Rules for Future LLMs Working on Jiraiya

Before changing code:

1. Read this `ROADMAP.md`.
2. Inspect the actual current file; do not rely only on this historical document.
3. Check function signatures before calling functions.
4. Make a backup before substantial changes.
5. Keep the existing working behavior unless the change is intentional.
6. Test syntax after Python changes.
7. Test the smallest affected component before restarting the whole system.
8. Never expose or commit secrets.
9. Do not replace a verified data-extraction pipeline with an unverified LLM guess.
10. Prefer fast, deterministic code for live-data extraction and let the LLM summarize verified data.
11. Keep local-first/privacy as the default architecture.
12. If an experimental change makes the system slower or less reliable, roll it back before continuing.

---

## 19. Current Handoff Summary

**Jiraiya is no longer just a basic local chatbot.** It currently has the foundations of a local AI assistant: local model inference, routing, encrypted memory, automatic memory analysis, relevant-memory retrieval, persistent sessions, a Python API, a responsive web UI, and web-search integration.

The project is currently in the **stabilization/integration stage**, not the autonomous-self-improvement stage.

The most important immediate goals are:

> **UI stability + session continuity + memory reliability + verified web answers + performance.**

Do not sacrifice factual reliability for speed, and do not sacrifice the existing working architecture merely to add a more complex experimental feature.

---

## 20. Change Log Convention

Future development should append concise entries below this line using:

```text
## YYYY-MM-DD — Change title
- What changed
- Why it changed
- Tests performed
- Known limitations
```

This keeps the document useful as a living handoff for future LLMs and developers.
