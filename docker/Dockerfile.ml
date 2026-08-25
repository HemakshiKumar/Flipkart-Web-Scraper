# ==============================================================================
# ML Model Dockerfile - Flipkart Recommendation Model & Notebook Environment
# ==============================================================================
FROM python:3.12-slim AS base

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    JUPYTER_PORT=8888

WORKDIR /workspace

# Install ML and Jupyter dependencies
COPY docker/requirements-ml.txt /workspace/requirements-ml.txt
RUN pip install -r /workspace/requirements-ml.txt

# Copy dataset, notebook, and ML pipeline runner
COPY "Web Scraping Project/" "/workspace/Web Scraping Project/"
COPY docker/ml_pipeline.py /workspace/ml_pipeline.py

# Create a symlink/copy of dataset in working directory for convenience
RUN cp "/workspace/Web Scraping Project/flipkart_data.csv" /workspace/flipkart_data.csv 2>/dev/null || true

# Expose JupyterLab port
EXPOSE 8888

# Default command: Start JupyterLab server with tokenless local access for container usage
# Alternative usage (CLI batch inference): docker run <image> python ml_pipeline.py "query"
CMD ["jupyter", "lab", "--ip=0.0.0.0", "--port=8888", "--no-browser", "--allow-root", "--ServerApp.token=''", "--ServerApp.password=''"]
