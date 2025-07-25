# Use official lightweight Python image
FROM python:3.11-slim

# Set working directory inside container
WORKDIR /app

# Copy only requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy all project files
COPY . .

# Expose default Chainlit port (you can change this if needed)
EXPOSE 8000

# Start the Chainlit app
CMD ["chainlit", "run", "main.py", "-w"]
