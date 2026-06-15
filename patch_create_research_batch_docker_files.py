from pathlib import Path

root = Path(r"C:\Workspaces\port_strategy_research")

requirements = """psycopg2-binary
pandas
numpy
"""

dockerfile = """FROM python:3.13-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

COPY port_strategy_research/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY port_strategy_common/ ./port_strategy_common/
COPY port_strategy_research/ ./port_strategy_research/

CMD ["python", "-m", "py_compile", "port_strategy_research/backtest_research_run.py"]
"""

(root / "requirements.txt").write_text(requirements, encoding="utf-8")
(root / "Dockerfile").write_text(dockerfile, encoding="utf-8")

print("[OK] created requirements.txt")
print("[OK] created Dockerfile")

print("")
print("--- requirements.txt ---")
print((root / "requirements.txt").read_text(encoding="utf-8"))

print("")
print("--- Dockerfile preview ---")
print((root / "Dockerfile").read_text(encoding="utf-8"))