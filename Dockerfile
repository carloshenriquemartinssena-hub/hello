FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt constraints.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY crm ./crm
RUN useradd --create-home crm && mkdir -p /app/data && chown -R crm:crm /app
USER crm
EXPOSE 10000
CMD ["sh", "-c", "uvicorn crm.main:app --host 0.0.0.0 --port ${PORT:-10000} --proxy-headers --forwarded-allow-ips='*'"]
