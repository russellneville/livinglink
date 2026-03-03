# livinglink

Providing dementia support for seniors through a caring and supportive digital assistant.

## Development status

**Phase 3 / pre-production. Not for clinical or production use.**

All LLM, STT, and TTS providers are mocks using simple keyword triggers — not clinical
thresholds or real models. The escalation and emergency workflows are exercised in tests
but have not been evaluated against real caregiving scenarios. Phase 4 (real providers,
safety evaluation framework) has not begun.

This repository is a research and development prototype. Do not use it with real patients
or caregivers in any phase prior to Phase 4 completion and independent safety evaluation.

### What this repository includes
- Safety, privacy, and incident response documentation (`docs/`)
- A phased roadmap and requirements baseline
- Phase 1–3 implementation: event bus, policy gate, mock providers, executor,
  caregiver escalation engine, and desktop UI pipeline

## Quick start
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
pytest
python -m livinglink.app.main
```

Optional desktop UI dependency:
```bash
pip install -e .[ui]
python -c "from livinglink.ui.window import launch_ui; launch_ui()"
```
