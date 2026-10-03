FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY packages ./packages
COPY services ./services
COPY apps/api ./apps/api
COPY config ./config
COPY migrations ./migrations
COPY scripts ./scripts
COPY alembic.ini ./
RUN pip install --no-cache-dir uv && uv sync --frozen --no-dev --all-packages
EXPOSE 8300
CMD ["uv", "run", "--no-dev", "uvicorn", "radar_api.app:app", "--host", "0.0.0.0", "--port", "8300"]
