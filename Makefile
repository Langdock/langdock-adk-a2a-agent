.PHONY: help install install-dev clean test lint format playground a2a deploy-dev deploy-staging deploy-prod

# Default target
help:
	@echo "Statista Agent - Development Commands"
	@echo ""
	@echo "Setup & Installation:"
	@echo "  make install          Install production dependencies"
	@echo "  make install-dev      Install development dependencies"
	@echo ""
	@echo "Development:"
	@echo "  make playground       Run local playground with A2A server"
	@echo "  make a2a             Run A2A server on port 8001"
	@echo "  make test            Run tests"
	@echo "  make lint            Run linters (ruff, mypy)"
	@echo "  make format          Format code with black and ruff"
	@echo ""
	@echo "Deployment:"
	@echo "  make deploy          Deploy to production environment"
	@echo ""
	@echo "Utilities:"
	@echo "  make clean           Remove build artifacts and cache"

# Installation targets
install:
	@echo "Installing production dependencies..."
	pip install -e .

install-dev:
	@echo "Installing development dependencies..."
	pip install -e ".[dev]"

# Development targets
playground:
	@echo "Starting A2A playground..."
	@echo "Access at http://localhost:8001"
	python a2a_rootagent.py

a2a:
	@echo "Starting A2A server on port 8001..."
	python a2a_rootagent.py

test:
	@echo "Running tests..."
	pytest tests/ -v

lint:
	@echo "Running linters..."
	ruff check .
	mypy statista_agent/

format:
	@echo "Formatting code..."
	black .
	ruff check --fix .

# Deployment targets (require gcloud CLI and Docker)
deploy:
	@echo "Deploying A2A agent to Cloud Run..."
	@if [ -z "$(GCP_PROJECT)" ]; then \
		echo "Error: GCP_PROJECT environment variable is not set"; \
		exit 1; \
	fi
	@if [ -z "$(GCP_REGION)" ]; then \
		echo "Error: GCP_REGION environment variable is not set"; \
		exit 1; \
	fi
	@echo "Step 1: Building Docker image..."
	docker build -t $(GCP_REGION)-docker.pkg.dev/$(GCP_PROJECT)/langdock-agents/statista-agent:latest .
	@echo "Step 2: Configuring Docker authentication..."
	gcloud auth configure-docker $(GCP_REGION)-docker.pkg.dev --quiet
	@echo "Step 3: Pushing image to Artifact Registry..."
	docker push $(GCP_REGION)-docker.pkg.dev/$(GCP_PROJECT)/langdock-agents/statista-agent:latest
	@echo "Step 4: Deploying to Cloud Run..."
	gcloud run deploy statista-a2a-agent \
		--image $(GCP_REGION)-docker.pkg.dev/$(GCP_PROJECT)/langdock-agents/statista-agent:latest \
		--platform managed \
		--region $(GCP_REGION) \
		--project $(GCP_PROJECT) \
		--port 8001 \
		--memory 1Gi \
		--cpu 1 \
		--min-instances 0 \
		--max-instances 10 \
		--allow-unauthenticated \
		--set-env-vars GOOGLE_GENAI_USE_VERTEXAI=true,GOOGLE_CLOUD_PROJECT=$(GCP_PROJECT),GOOGLE_CLOUD_LOCATION=$(GCP_REGION)

# Utility targets
clean:
	@echo "Cleaning build artifacts..."
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.log" -delete
