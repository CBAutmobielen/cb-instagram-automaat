# Exact dezelfde omgeving als waarin de referentieslides zijn gemaakt:
# Playwright 1.56.0 (Chromium 141.0.7390.37), Pillow 12.3.0.
FROM mcr.microsoft.com/playwright/python:v1.56.0-noble
WORKDIR /kit
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["bash", "run.sh"]
