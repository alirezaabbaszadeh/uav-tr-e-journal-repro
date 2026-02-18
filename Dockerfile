FROM python:3.12-slim

WORKDIR /workspace

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-lock.txt /tmp/requirements-lock.txt
RUN pip install --no-cache-dir -r /tmp/requirements-lock.txt

COPY pyproject.toml README.md /workspace/
COPY src /workspace/src
COPY configs /workspace/configs
COPY scripts /workspace/scripts

RUN pip install --no-cache-dir -e .

CMD ["python", "-m", "uavtre.run_experiments", "--config", "configs/base.json", "--profile", "quick", "--output", "outputs/results_main.csv", "--max-cases", "1"]
