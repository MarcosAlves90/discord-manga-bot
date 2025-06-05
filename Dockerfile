FROM python:3.11-slim

WORKDIR /app

# Copiar apenas o arquivo requirements.txt primeiro para aproveitar o cache de camadas
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar o restante do código
COPY . .

# Configuração de ambiente
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Criar pasta para logs e dados
RUN mkdir -p /app/data /app/logs

# Comando para iniciar o bot
CMD ["python", "main.py"]