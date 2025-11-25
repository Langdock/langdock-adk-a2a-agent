# Deployment Guide: Vertex AI Agent Engine

This guide walks you through deploying the Statista Agent to Google Cloud's Vertex AI Agent Engine with automated CI/CD via GitHub Actions.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Google Cloud Setup](#google-cloud-setup)
3. [Workload Identity Federation](#workload-identity-federation)
4. [GitHub Configuration](#github-configuration)
5. [Deployment](#deployment)
6. [Verification](#verification)
7. [Troubleshooting](#troubleshooting)

## Prerequisites

- Google Cloud account with billing enabled
- GitHub repository access
- gcloud CLI installed ([Install Guide](https://cloud.google.com/sdk/docs/install))
- Statista API key

## Google Cloud Setup

### 1. Create or Select Project

```bash
# Create new project (optional)
export PROJECT_ID="your-project-id"
gcloud projects create $PROJECT_ID

# Set as active project
gcloud config set project $PROJECT_ID
```

### 2. Enable Required APIs

```bash
gcloud services enable \
  aiplatform.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  iam.googleapis.com \
  iamcredentials.googleapis.com \
  cloudresourcemanager.googleapis.com
```

### 3. Create Artifact Registry Repository

```bash
gcloud artifacts repositories create agents \
  --repository-format=docker \
  --location=us-central1 \
  --description="Container images for AI agents"
```

### 4. Create Service Account

```bash
# Create service account for deployment
gcloud iam service-accounts create github-actions-deployer \
  --display-name="GitHub Actions Deployer" \
  --description="Service account for deploying agents from GitHub Actions"

# Get the service account email
export SA_EMAIL="github-actions-deployer@${PROJECT_ID}.iam.gserviceaccount.com"
```

### 5. Grant Permissions

```bash
# Vertex AI permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/aiplatform.user"

# Artifact Registry permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/artifactregistry.writer"

# Cloud Build permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/cloudbuild.builds.editor"

# Storage permissions (for staging)
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/storage.admin"
```

## Workload Identity Federation

Set up Workload Identity Federation to allow GitHub Actions to authenticate without service account keys.

### 1. Create Workload Identity Pool

```bash
gcloud iam workload-identity-pools create "github-pool" \
  --project="${PROJECT_ID}" \
  --location="global" \
  --display-name="GitHub Actions Pool"
```

### 2. Create Workload Identity Provider

```bash
# Replace GITHUB_ORG with your GitHub organization name
export GITHUB_ORG="Langdock"
export GITHUB_REPO="langdock-adk-a2a-agent"

gcloud iam workload-identity-pools providers create-oidc "github-provider" \
  --project="${PROJECT_ID}" \
  --location="global" \
  --workload-identity-pool="github-pool" \
  --display-name="GitHub Provider" \
  --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository,attribute.repository_owner=assertion.repository_owner" \
  --attribute-condition="assertion.repository_owner == '${GITHUB_ORG}'" \
  --issuer-uri="https://token.actions.githubusercontent.com"
```

### 3. Allow Service Account Impersonation

```bash
gcloud iam service-accounts add-iam-policy-binding "${SA_EMAIL}" \
  --project="${PROJECT_ID}" \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/$(gcloud projects describe ${PROJECT_ID} --format='value(projectNumber)')/locations/global/workloadIdentityPools/github-pool/attribute.repository/${GITHUB_ORG}/${GITHUB_REPO}"
```

### 4. Get Provider Resource Name

```bash
# Save this value for GitHub secrets
gcloud iam workload-identity-pools providers describe "github-provider" \
  --project="${PROJECT_ID}" \
  --location="global" \
  --workload-identity-pool="github-pool" \
  --format="value(name)"
```

The output will look like:
```
projects/123456789/locations/global/workloadIdentityPools/github-pool/providers/github-provider
```

## GitHub Configuration

### 1. Add Repository Secrets

Go to your GitHub repository → Settings → Secrets and variables → Actions → New repository secret

Add the following secrets:

| Secret Name | Value | Description |
|-------------|-------|-------------|
| `GCP_PROJECT` | `your-project-id` | Your GCP project ID |
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | `projects/.../github-provider` | Full provider resource name from step 3.4 |
| `GCP_SERVICE_ACCOUNT` | `github-actions-deployer@...` | Service account email |
| `STATISTA_API_KEY` | `your-statista-api-key` | Your Statista API key |

### 2. Create Production Environment

1. Go to repository Settings → Environments
2. Click "New environment"
3. Name it `production`
4. (Optional) Add protection rules:
   - Required reviewers
   - Wait timer
   - Deployment branches (main only)

## Deployment

### Automatic Deployment (Recommended)

Every push to `main` triggers automatic deployment:

```bash
git add .
git commit -m "Deploy to production"
git push origin main
```

Monitor the deployment:
1. Go to Actions tab in GitHub
2. Click on the latest workflow run
3. Watch the deployment progress

### Manual Deployment via Workflow

1. Go to Actions → Deploy to Production
2. Click "Run workflow"
3. Select branch: `main`
4. Click "Run workflow"

### Manual Deployment via CLI

```bash
# Authenticate with Google Cloud
gcloud auth application-default login

# Set environment variables
export GCP_PROJECT="your-project-id"
export GCP_REGION="us-central1"

# Deploy using Makefile
make deploy

# Or deploy using ADK CLI directly
adk deploy agent_engine \
  --agent-module agent_engine_app \
  --display-name "Statista Agent" \
  --project $GCP_PROJECT \
  --region $GCP_REGION
```

## Verification

### 1. Check Deployment Status

```bash
# List deployed agents
gcloud ai agents list \
  --project=$GCP_PROJECT \
  --region=us-central1

# Get agent details
gcloud ai agents describe AGENT_ID \
  --project=$GCP_PROJECT \
  --region=us-central1
```

### 2. View Logs

```bash
# View recent logs
gcloud logging read "resource.type=vertex_ai_agent_engine" \
  --project=$GCP_PROJECT \
  --limit=50 \
  --format=json

# Stream logs in real-time
gcloud logging tail "resource.type=vertex_ai_agent_engine" \
  --project=$GCP_PROJECT
```

### 3. Test the Agent

```bash
# Test via ADK CLI
adk test agent_engine \
  --agent-id=AGENT_ID \
  --project=$GCP_PROJECT \
  --region=us-central1 \
  --query="Find revenue statistics for BASF"
```

### 4. Check Container Images

```bash
# List images in Artifact Registry
gcloud artifacts docker images list \
  us-central1-docker.pkg.dev/$GCP_PROJECT/agents/statista-agent
```

## Troubleshooting

### Authentication Issues

**Problem:** Workload Identity Federation fails

**Solution:**
```bash
# Verify pool exists
gcloud iam workload-identity-pools describe github-pool \
  --location=global \
  --project=$GCP_PROJECT

# Verify provider exists
gcloud iam workload-identity-pools providers describe github-provider \
  --workload-identity-pool=github-pool \
  --location=global \
  --project=$GCP_PROJECT

# Check service account bindings
gcloud iam service-accounts get-iam-policy $SA_EMAIL
```

### Build Failures

**Problem:** Docker build fails in GitHub Actions

**Solutions:**
- Check Dockerfile syntax
- Verify all files are committed to git
- Check build logs in GitHub Actions
- Ensure base image is accessible

### Deployment Failures

**Problem:** ADK deploy command fails

**Solutions:**
```bash
# Check if APIs are enabled
gcloud services list --enabled --project=$GCP_PROJECT

# Verify service account permissions
gcloud projects get-iam-policy $GCP_PROJECT \
  --flatten="bindings[].members" \
  --filter="bindings.members:serviceAccount:${SA_EMAIL}"

# Check quota limits
gcloud compute project-info describe --project=$GCP_PROJECT
```

### Runtime Errors

**Problem:** Agent fails at runtime

**Solutions:**
1. Check environment variables in deployment
2. Verify Statista API key is valid
3. Check agent logs:
   ```bash
   gcloud logging read "resource.type=vertex_ai_agent_engine AND severity>=ERROR" \
     --project=$GCP_PROJECT \
     --limit=100
   ```

### Permission Errors

**Problem:** "Permission denied" errors

**Solutions:**
```bash
# Re-apply all permissions
./scripts/setup-permissions.sh  # If you create this helper script

# Or manually grant missing permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/MISSING_ROLE"
```

## Advanced Configuration

### Custom Region

To deploy in a different region, update:

1. `.github/workflows/deploy-production.yaml`:
   ```yaml
   env:
     GCP_REGION: "europe-west3"  # Change this
   ```

2. Artifact Registry location (if needed):
   ```bash
   gcloud artifacts repositories create agents \
     --repository-format=docker \
     --location=europe-west3
   ```

### Multiple Environments

To add staging environment:

1. Create staging project or use separate region
2. Duplicate workflow file as `deploy-staging.yaml`
3. Update environment references
4. Add staging secrets to GitHub

### Custom Build Steps

Edit [.cloudbuild/cloudbuild.yaml](.cloudbuild/cloudbuild.yaml) to customize build:
- Add pre-deployment tests
- Add security scanning
- Add custom validation steps

## Security Best Practices

1. ✅ Use Workload Identity Federation (no service account keys)
2. ✅ Enable branch protection for main branch
3. ✅ Require pull request reviews
4. ✅ Use GitHub environment protection rules
5. ✅ Rotate Statista API keys regularly
6. ✅ Enable audit logging in GCP
7. ✅ Use least-privilege IAM roles
8. ✅ Monitor deployment logs

## Cost Optimization

- Use appropriate machine types for builds
- Enable Cloud Build caching
- Clean up old container images:
  ```bash
  # Delete images older than 30 days
  gcloud artifacts docker images list \
    us-central1-docker.pkg.dev/$GCP_PROJECT/agents/statista-agent \
    --filter="createTime<$(date -d '30 days ago' --iso-8601)" \
    --format="get(package)" | \
    xargs -I {} gcloud artifacts docker images delete {}
  ```

## Support

- **ADK Documentation:** https://google.github.io/adk-docs/
- **Vertex AI Agent Engine:** https://cloud.google.com/vertex-ai/docs/agent-engine
- **GitHub Issues:** https://github.com/Langdock/langdock-adk-a2a-agent/issues

---

**Last Updated:** 2025-11-25
**Version:** 1.0.0
