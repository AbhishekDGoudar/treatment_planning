FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
# The ollama Python client reads OLLAMA_HOST natively.
# host.docker.internal resolves to the Mac host in Docker Desktop.
# On Linux override with: docker run -e OLLAMA_HOST=http://172.17.0.1:11434
ENV OLLAMA_HOST=http://host.docker.internal:11434

WORKDIR /app

COPY . /app

RUN pip install --upgrade pip && pip install uv
ENV UV_PROJECT_ENVIRONMENT=/app/.venv
RUN uv venv /app/.venv --clear
RUN uv sync --frozen
ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8501

CMD ["streamlit", "run", "treatment_planning.py", "--server.address=0.0.0.0", "--server.port=8501"]
