# -------------------------
# Fly.io Streamlit Dockerfile
# -------------------------

FROM python:3.10-slim

# Prevent interactive prompts during install
ENV DEBIAN_FRONTEND=noninteractive

# Create working directory
WORKDIR /app

# Install minimal system dependencies (no atlas needed)
RUN apt-get update && apt-get install -y \
    build-essential \
    libffi-dev \
    curl \
    wget \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY . /app

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose Streamlit port
EXPOSE 8080

# Streamlit configuration
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_SERVER_PORT=8080
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
ENV STREAMLIT_SERVER_ENABLECORS=false
# ENV STREAMLIT_SERVER_ENABLEXSRSFPROTECTION=false

# Entrypoint
CMD ["streamlit", "run", "roboadvisor.py", "--server.port=8080", "--server.address=0.0.0.0"]
