FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Expose default port (Chainlit will use it)
EXPOSE 8000

# Run using environment-provided PORT
CMD ["sh", "-c", "chainlit run main.py --port ${PORT} --host 0.0.0.0"]
