FROM python:3.11-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PIP_DEFAULT_TIMEOUT=300
COPY requirements.txt .
# Prefer the small CPU-only torch build, but fall back to regular PyPI if that server is unreachable
RUN pip install --extra-index-url https://download.pytorch.org/whl/cpu torch \
    && pip install -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]