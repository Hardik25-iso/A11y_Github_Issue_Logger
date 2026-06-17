FROM mcr.microsoft.com/playwright/python:v1.52.0-jammy

WORKDIR /app

# Install Python dependencies (playwright already present in base image)
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt \
    && pip install --no-cache-dir playwright==1.52.0

# Copy source
COPY . .

ENV PYTHONPATH=/app
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

EXPOSE 8080
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8080"]
