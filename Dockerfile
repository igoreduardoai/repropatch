FROM node:22-bookworm-slim AS node-runtime
FROM python:3.13-slim-bookworm
WORKDIR /app
COPY --from=node-runtime /usr/local/bin/node /usr/local/bin/node
RUN apt-get update && apt-get install -y --no-install-recommends libstdc++6 libgcc-s1 && rm -rf /var/lib/apt/lists/*
RUN useradd --uid 10001 --create-home appuser
COPY pyproject.toml ./
COPY repropatch ./repropatch
RUN pip install --no-cache-dir .
COPY web ./web
COPY fixtures ./fixtures
COPY evaluation/fixture-independent.mjs ./evaluation/fixture-independent.mjs
RUN mkdir -p /data && chown -R appuser:appuser /data /app
ENV REPROPATCH_DATA_DIR=/data PYTHONDONTWRITEBYTECODE=1
USER appuser
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "repropatch.api:app", "--host", "0.0.0.0", "--port", "8000"]
