FROM python:3.12-bookworm
WORKDIR /app
COPY requirements.txt .
RUN python -m pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt
COPY app ./app
RUN mkdir -p uploads exports
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
