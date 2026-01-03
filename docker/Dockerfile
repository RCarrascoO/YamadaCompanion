FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias del sistema necesarias para compilación (si las hay)
RUN apt-get update && apt-get install -y \
    gcc \
    libffi-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements e instalar
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código fuente
COPY . .

# Comando por defecto
CMD ["python", "-m", "src.main"]
