# Project Guidelines

## Behavior
- Code only. No explanations unless asked.
- Output diffs, not full files.
- No explanation after completing a task.
- Respond short and direct.

## Coding Rules (Karpathy)
- State assumptions before coding. Ask if uncertain.
- Minimum code that solves the problem. Nothing speculative.
- Touch only what was requested. Do not refactor adjacent code.
- Remove only imports/variables that YOUR changes made unused.
- Define success criteria before starting multi-step tasks.

## Project Context
- Stack: Python, Streamlit, Plotly
- Entry point: `dashboard_tv_novo.py` (kept for AWS compatibility)
- Background process: `updater.py` (never rename or move)
- Deploy: GitHub commit → SSH git pull on AWS
- Virtual env: `/home/ubuntu/dashboard/venv`

## Modular Structure (target)
- `src/config.py` — constants, env vars
- `src/auth/token.py` — token renewal
- `src/data/` — api, cache, aliases, transforms
- `src/utils/` — time helpers, formatters
- `src/ui/` — styles, cards, modals
- `src/charts/` — all Plotly charts
- `src/views/` — all render_* functions
- `dashboard_tv_novo.py` — entrypoint only (~50 lines), imports from src/

## Safety Rules
- Never rename `dashboard_tv_novo.py` or `updater.py`
- Never modify `.env`
- Always keep `__init__.py` in every new folder
- After each module extraction, confirm imports resolve before moving to the next
