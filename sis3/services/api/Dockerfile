FROM public.ecr.aws/docker/library/python:3.13-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:0.13.9 /uv /bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=0
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project

FROM public.ecr.aws/docker/library/python:3.13-slim AS runner
RUN useradd --system --uid 10001 appuser
USER appuser
WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY main.py ./
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["python", "main.py"]