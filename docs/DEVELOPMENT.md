# Jiraiya AI — Development Guide

This document is for future developers and AI coding agents working on Jiraiya.

## Before changing anything

1. Read `ROADMAP.md`.
2. Read `docs/ARCHITECTURE.md`.
3. Inspect the actual current file(s).
4. Check existing function signatures and imports.
5. Make a backup before substantial source replacement.
6. Make the smallest change that solves the problem.

## Test order

Prefer this sequence:

```text
syntax check
   ↓
unit/component test
   ↓
API endpoint test
   ↓
UI integration test
```

For Python files:

```bash
python -m py_compile path/to/file.py
```

## Safe source editing workflow

For manual Termux edits, the project's preferred replacement workflow includes removing the temporary/replacement file before recreating it. Keep backups of important source files before replacement.

Example:

```bash
cd ~/jiraiya
cp agent.py agent.py.before_change
rm -f replacement.py
```

Project-local temporary files are preferred over `/tmp` because `/tmp` may not be writable in the Termux environment used for development.

## Secrets

Never commit:

- `master.key`
- API keys
- passwords
- tokens
- `.env` files containing credentials
- private memory databases
- private session data
- local model files

Review `.gitignore` before the first push of the local project.

## Web-data rule

For live information, especially prices and rates:

- retrieve sources first
- verify/compare them
- extract date and value
- only then ask the LLM to summarize

Never allow a small local model to invent a live value because a web result was incomplete.

## Performance rule

The target hardware is Android/Termux with small local models. Avoid unnecessary network calls, full-page fetching, oversized prompts and excessive context.

Benchmark slow paths before adding complexity.

## Session rule

A user conversation should remain one session. Do not create a new session for every message.

When changing session behavior, test:

1. new chat
2. multiple messages
3. reload page
4. open an older chat
5. rename chat
6. delete chat

## Memory rule

Use the existing encrypted memory subsystem. Do not create duplicate plaintext memory stores.

Automatic memory policy:

- stable/important → long-term
- temporary/uncertain → 30-day cache
- irrelevant → discard
- secrets → never store

Only relevant memories should be included in the model context.

## Self-improvement rule

Do not enable autonomous source modification as a normal workflow yet. The current experimental self-improvement engine has demonstrated unreliable structured output on the available small model.

When eventually revisited, every autonomous modification should have:

- backup
- bounded scope
- generated diff
- syntax validation
- tests
- rollback
- human approval for risky changes

## Commit convention

Use concise commits describing the actual change, for example:

```text
feat: add knowledge document retrieval
fix: prevent duplicate session messages
docs: update roadmap
refactor: simplify web source extraction
```

## Change documentation

After meaningful changes, update `ROADMAP.md` using its change-log convention. Record:

- what changed
- why
- tests performed
- known limitations

## Definition of done

A feature is not considered complete merely because the code compiles. It should be tested at the appropriate layer and its known limitations should be recorded.
