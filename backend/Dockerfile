FROM python:3.12-slim

# Dependências de sistema para OCR e processamento (opcional - falha silenciosamente se repositórios inacessíveis)
RUN apt-get update -o Acquire::Retries=3 && \
    apt-get install -y --no-install-recommends \
        tesseract-ocr \
        tesseract-ocr-por \
        tesseract-ocr-eng \
        libgomp1 \
        libglib2.0-0 \
        libsm6 \
        libxext6 \
        libxrender-dev \
        ghostscript \
        poppler-utils \
        curl \
    && rm -rf /var/lib/apt/lists/* \
    || (echo "Warning: apt-get failed, OCR features may be unavailable" && apt-get clean)

WORKDIR /app

# Copia e instala dependências Python (cache-friendly)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
        --trusted-host pypi.org --trusted-host files.pythonhosted.org --trusted-host pypi.python.org && \
    pip install --no-cache-dir -r requirements.txt \
        --trusted-host pypi.org --trusted-host files.pythonhosted.org --trusted-host pypi.python.org

# Copia código-fonte
COPY . .

# Usuário não-root para segurança
RUN useradd -m -u 1001 officejoe && chown -R officejoe:officejoe /app
USER officejoe

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
