# Jiraiya-Cyber 🛡️

Authorization-first cybersecurity assistant built on the Jiraiya architecture.

## Workflow

**Discover → Analyze → Verify proposal → Ask permission → Bounded verification → Evidence → Report**

### Included

- Explicit target scope with host/path allowlists and exclusions
- Passive, bounded HTTP reconnaissance
- Candidate security-header findings
- Finding lifecycle and evidence capture
- Verification plans
- Per-finding, per-target, per-action authorization
- Authorization expiry and attempt limits
- Bounded authorized verification executor
- Structured bug-bounty report generation
- Cyber-focused browser UI
- Automated Python tests through GitHub Actions

## Safety boundary

The verification executor is deliberately narrow. It performs one ordinary GET against the exact authorized target after authorization is approved. It is not a generic shell, crawler, fuzzing engine, credential attack tool, or unrestricted exploit runner.

Any future active-testing module should preserve the same scope and authorization gates.

## Run locally

```bash
python -m unittest discover -s cyber -p 'test_*.py' -v
python api/server.py
```

The API server is localhost-oriented and exposes the Cyber endpoints documented in CYBER.md.

## Main API

- POST /api/cyber/scope
- POST /api/cyber/recon
- GET /api/cyber/findings
- POST /api/cyber/finding/<id>/verification
- POST /api/cyber/finding/<id>/authorization
- POST /api/cyber/authorization/<id>/approve
- POST /api/cyber/authorization/<id>/consume
- POST /api/cyber/report/<finding_id>

Use only against assets you are authorized to assess.
