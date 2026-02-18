# Build Instructions

## Python (venv)
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-lock.txt
pip install -e .
python -m uavtre.run_experiments --config configs/base.json --profile quick --output outputs/results_main.csv --max-cases 1
```

## Docker
```bash
docker build -t uavtre:1.0.0 .
docker run --rm -v "$PWD":/workspace -w /workspace uavtre:1.0.0 \
  python -m uavtre.run_experiments --config configs/base.json --profile quick --output outputs/results_main.csv --max-cases 1
```
