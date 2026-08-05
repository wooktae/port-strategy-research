FROM python:3.13-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY .devops/packages/port_strategy_common-1.0.0-py3-none-any.whl /tmp/packages/port_strategy_common-1.0.0-py3-none-any.whl

RUN pip install --no-cache-dir --no-deps /tmp/packages/port_strategy_common-1.0.0-py3-none-any.whl \
    && python -c "import importlib.metadata; version = importlib.metadata.version('port-strategy-common'); assert version == '1.0.0', version"
COPY *.py ./port_strategy_research/
COPY strategy_profiles/ ./strategy_profiles/

CMD ["python", "-m", "py_compile", "port_strategy_research/backtest_research_run.py"]
