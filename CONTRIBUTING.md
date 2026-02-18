# Contributing

## Branch and Commit Rules
- Default branch: `main`.
- Use focused commits with test evidence.
- Do not merge changes that break CSV contracts in `src/uavtre/io/schema.py`.

## Development Setup
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-lock.txt
pip install -e .
```

## Required Checks
```bash
pytest
python -m uavtre.run_experiments --config configs/base.json --profile quick --output outputs/results_main.csv --max-cases 1
```

## Scientific Guardrails
- Keep claim policy by size unchanged unless explicitly re-locked.
- Keep baseline fairness budget explicit and comparable.
- Keep output schemas backward compatible.
