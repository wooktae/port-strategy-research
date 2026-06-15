FROM python:3.13-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

COPY port_strategy_research/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY port_strategy_common/ ./port_strategy_common/
COPY port_strategy_research/ ./port_strategy_research/

CMD ["python", "-m", "py_compile", "port_strategy_research/backtest_research_run.py"]
