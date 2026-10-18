FROM python:3.11-slim

WORKDIR /app

# Install system font dependencies for ReportLab PDF rendering
RUN apt-get update && apt-get install -y --no-install-recommends \
    fonts-nanum \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Expose port (Render/Hugging Face use PORT env var)
ENV PORT=8080
EXPOSE 8080

CMD ["python", "main.py"]
