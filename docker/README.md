# Docker Configuration for Flipkart Product Recommendation Engine

This folder contains the Docker configuration files for containerizing the **Backend API** and the **Machine Learning model / Notebook environment**.

---

## Architecture Overview

| Component | Dockerfile | Default Port | Description |
| :--- | :--- | :--- | :--- |
| **Backend Service** | [`Dockerfile.backend`](file:///docker/Dockerfile.backend) | `8000` | FastAPI service with Uvicorn, health checks, caching, and recommendation API endpoints. |
| **ML Model / Jupyter** | [`Dockerfile.ml`](file:///docker/Dockerfile.ml) | `8888` | Machine learning environment with TF-IDF model vectorizer, JupyterLab workspace, and batch inference CLI. |

---

## 1. Backend Service

### Build the Image
```bash
docker build -f docker/Dockerfile.backend -t flipkart-scraper-backend .
```

### Run the Container
```bash
docker run -d -p 8000:8000 --name flipkart-backend flipkart-scraper-backend
```

### Verify Backend Health
```bash
curl http://localhost:8000/api/health
```

Expected output:
```json
{"status":"ok","timestamp":"...","dataset_cached":true}
```

### Test Recommendation API Endpoint
```bash
curl -X POST http://localhost:8000/api/recommend \
  -H "Content-Type: application/json" \
  -d "{\"query\": \"bluetooth neckband\", \"requirements\": \"under 1000 with mic\"}"
```

---

## 2. Machine Learning Model

### Build the Image
```bash
docker build -f docker/Dockerfile.ml -t flipkart-scraper-ml .
```

### Run Interactive JupyterLab Workspace
```bash
docker run -d -p 8888:8888 --name flipkart-ml flipkart-scraper-ml
```
Open **`http://localhost:8888`** in your browser to inspect or run `web-scraping-project/code file.ipynb`.

### Run Standalone ML Model Inference (CLI)
You can directly run TF-IDF queries against the model without starting a web server:

```bash
docker run --rm flipkart-scraper-ml python ml_pipeline.py "Bluetooth neckband with mic and 50-hour playback under 1000" --top-n 5
```

---

## 3. Using Docker Compose (Both Services)

To start both services together:

```bash
docker compose up -d
```

To build or rebuild images:

```bash
docker compose build
```

To stop all running containers:

```bash
docker compose down
```
