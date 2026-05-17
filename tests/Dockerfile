FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    "pytest>=8.0.0" \
    "pytest-asyncio>=0.23.0"

COPY backend/ ./backend/
COPY tests/ ./tests/
COPY pytest.ini .

CMD ["pytest", "-v", "--tb=short"]
