# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy only dependency files first (for better layer caching)
COPY requirements.txt ./
COPY pyproject.toml ./

# Install Python dependencies (this layer gets cached if requirements don't change)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Now copy the rest of the application code
COPY agent_engine_app.py ./
COPY a2a_rootagent.py ./
COPY logging_config.py ./
COPY agent_card.json ./
COPY statista_agent/ ./statista_agent/

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Expose the A2A port
EXPOSE 8080

# Run the A2A agent
CMD ["python", "a2a_rootagent.py"]
