FROM python:3.12-slim AS builder

ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock README.md ./
COPY src/ ./src/

RUN uv sync \
    --frozen \
    --no-dev \
    --no-editable


FROM python:3.12-slim AS runtime

ENV PATH="/app/.venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

RUN groupadd --system johnny \
    && useradd \
        --system \
        --gid johnny \
        --home-dir /app \
        --no-create-home \
        johnny

COPY --from=builder --chown=johnny:johnny /app/.venv /app/.venv

USER johnny

EXPOSE 8000

CMD ["jj", "serve", "--host", "0.0.0.0", "--port", "8000"]