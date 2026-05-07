FROM python:3.12-slim

WORKDIR /app

# Dependências de sistema mínimas para esta fase
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Dependências Python (separado do código para aproveitar cache de imagem)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Código-fonte
COPY . .

# Usuário não-root
RUN useradd -m -u 1001 officejoe && chown -R officejoe:officejoe /app
USER officejoe

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
