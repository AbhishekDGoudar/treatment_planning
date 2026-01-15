FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY . /app

RUN pip install --upgrade pip && pip install uv
ENV UV_PROJECT_ENVIRONMENT=/app/.venv
RUN uv venv /app/.venv
RUN uv sync --frozen
ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8501

CMD ["streamlit", "run", "treatment_planning.py", "--server.address=0.0.0.0", "--server.port=8501"]
