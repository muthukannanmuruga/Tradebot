# Docker Image Deployment Guide

This guide shows how to build a Docker image locally, push it to a registry, and deploy it on EC2.

---

## Option A: Using Docker Hub (Easiest)

### Step 1: Create Docker Hub Account
1. Go to https://hub.docker.com/
2. Sign up for a free account
3. Note your username (e.g., `yourname`)

### Step 2: Build and Push Image (On Your Windows Machine)

```powershell
# Login to Docker Hub
docker login

# Build the image with your Docker Hub username
docker build -t yourname/ai-trading-bot:latest .

# Push to Docker Hub
docker push yourname/ai-trading-bot:latest

# Verify it was uploaded
# Check https://hub.docker.com/r/yourname/ai-trading-bot
```

### Step 3: Update docker-compose.yml for Production

Create a new file `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  trading-bot:
    image: yourname/ai-trading-bot:latest  # Use your Docker Hub image
    container_name: ai-trading-bot
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
      - ./.env:/app/.env
    environment:
      - BINANCE_API_KEY=${BINANCE_API_KEY}
      - BINANCE_API_SECRET=${BINANCE_API_SECRET}
      - BINANCE_TESTNET_API_KEY=${BINANCE_TESTNET_API_KEY}
      - BINANCE_TESTNET_API_SECRET=${BINANCE_TESTNET_API_SECRET}
      - DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY}
      - DATABASE_URL=${DATABASE_URL}
      - BINANCE_TESTNET=${BINANCE_TESTNET:-True}
      - TRADING_PAIR=${TRADING_PAIR:-BTCUSDT}
      - TRADING_AMOUNT_QUOTE=${TRADING_AMOUNT_QUOTE:-1}
      - CHECK_INTERVAL_SECONDS=${CHECK_INTERVAL_SECONDS:-60}
      - MAX_DAILY_TRADES=${MAX_DAILY_TRADES:-10}
      - PYTHONUNBUFFERED=1
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

volumes:
  data:
    driver: local
```

### Step 4: Deploy on EC2

```bash
# SSH into EC2
ssh -i "your-key.pem" ec2-user@<EC2-PUBLIC-IP>

# Create project directory
mkdir -p ~/trading-bot
cd ~/trading-bot

# Copy docker-compose.prod.yml to EC2 (from your Windows machine)
# Using SCP from Windows PowerShell:
scp -i "your-key.pem" docker-compose.prod.yml ec2-user@<EC2-PUBLIC-IP>:~/trading-bot/

# Or create it directly on EC2
nano docker-compose.prod.yml
# Paste the content above, save with Ctrl+X, Y, Enter

# Create .env file
nano .env
# Paste your environment variables, save

# Pull and run the image
docker-compose -f docker-compose.prod.yml pull
docker-compose -f docker-compose.prod.yml up -d

# View logs
docker-compose -f docker-compose.prod.yml logs -f
```

---

## Option B: Using AWS ECR (More Secure for Production)

### Step 1: Create ECR Repository

```bash
# Install AWS CLI on your Windows machine if not already installed
# Download from: https://aws.amazon.com/cli/

# Configure AWS credentials
aws configure

# Create ECR repository
aws ecr create-repository --repository-name ai-trading-bot --region us-east-1

# Note the repository URI (e.g., 123456789012.dkr.ecr.us-east-1.amazonaws.com/ai-trading-bot)
```

### Step 2: Build and Push to ECR (On Your Windows Machine)

```powershell
# Get ECR login token
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 123456789012.dkr.ecr.us-east-1.amazonaws.com

# Build the image
docker build -t ai-trading-bot:latest .

# Tag for ECR
docker tag ai-trading-bot:latest 123456789012.dkr.ecr.us-east-1.amazonaws.com/ai-trading-bot:latest

# Push to ECR
docker push 123456789012.dkr.ecr.us-east-1.amazonaws.com/ai-trading-bot:latest
```

### Step 3: Setup EC2 IAM Role for ECR Access

1. **Go to AWS IAM Console**
2. **Create IAM Role:**
   - Trusted entity: EC2
   - Attach policy: `AmazonEC2ContainerRegistryReadOnly`
   - Name: `EC2-ECR-Access`
3. **Attach Role to EC2:**
   - Go to EC2 Console
   - Select your instance
   - Actions → Security → Modify IAM Role
   - Select `EC2-ECR-Access`

### Step 4: Deploy on EC2 with ECR

```bash
# SSH into EC2
ssh -i "your-key.pem" ec2-user@<EC2-PUBLIC-IP>

# Create project directory
mkdir -p ~/trading-bot
cd ~/trading-bot

# Install AWS CLI on EC2 (Amazon Linux 2023)
sudo yum install aws-cli -y

# Login to ECR (no credentials needed with IAM role)
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 123456789012.dkr.ecr.us-east-1.amazonaws.com

# Create docker-compose.prod.yml
nano docker-compose.prod.yml
```

**Paste this content (update with your ECR URI):**
```yaml
version: '3.8'

services:
  trading-bot:
    image: 123456789012.dkr.ecr.us-east-1.amazonaws.com/ai-trading-bot:latest
    container_name: ai-trading-bot
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
      - ./.env:/app/.env
    environment:
      - BINANCE_API_KEY=${BINANCE_API_KEY}
      - BINANCE_API_SECRET=${BINANCE_API_SECRET}
      - BINANCE_TESTNET_API_KEY=${BINANCE_TESTNET_API_KEY}
      - BINANCE_TESTNET_API_SECRET=${BINANCE_TESTNET_API_SECRET}
      - DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY}
      - DATABASE_URL=${DATABASE_URL}
      - BINANCE_TESTNET=${BINANCE_TESTNET:-True}
      - TRADING_PAIR=${TRADING_PAIR:-BTCUSDT}
      - TRADING_AMOUNT_QUOTE=${TRADING_AMOUNT_QUOTE:-1}
      - CHECK_INTERVAL_SECONDS=${CHECK_INTERVAL_SECONDS:-60}
      - MAX_DAILY_TRADES=${MAX_DAILY_TRADES:-10}
      - PYTHONUNBUFFERED=1
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

volumes:
  data:
    driver: local
```

```bash
# Create .env file
nano .env
# Paste your environment variables, save

# Pull and run the image
docker-compose -f docker-compose.prod.yml pull
docker-compose -f docker-compose.prod.yml up -d

# View logs
docker-compose -f docker-compose.prod.yml logs -f
```

---

## Updating Your Application

### When you make code changes:

#### For Docker Hub:
```powershell
# On Windows machine
docker build -t yourname/ai-trading-bot:latest .
docker push yourname/ai-trading-bot:latest

# On EC2
ssh -i "your-key.pem" ec2-user@<EC2-PUBLIC-IP>
cd ~/trading-bot
docker-compose -f docker-compose.prod.yml pull
docker-compose -f docker-compose.prod.yml up -d
```

#### For AWS ECR:
```powershell
# On Windows machine
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 123456789012.dkr.ecr.us-east-1.amazonaws.com
docker build -t ai-trading-bot:latest .
docker tag ai-trading-bot:latest 123456789012.dkr.ecr.us-east-1.amazonaws.com/ai-trading-bot:latest
docker push 123456789012.dkr.ecr.us-east-1.amazonaws.com/ai-trading-bot:latest

# On EC2
ssh -i "your-key.pem" ec2-user@<EC2-PUBLIC-IP>
cd ~/trading-bot
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 123456789012.dkr.ecr.us-east-1.amazonaws.com
docker-compose -f docker-compose.prod.yml pull
docker-compose -f docker-compose.prod.yml up -d
```

---

## Using Version Tags (Recommended)

Instead of using `latest` tag, use version numbers for better control:

```powershell
# Build with version tag
docker build -t yourname/ai-trading-bot:v1.0.0 .
docker push yourname/ai-trading-bot:v1.0.0

# Also tag as latest
docker tag yourname/ai-trading-bot:v1.0.0 yourname/ai-trading-bot:latest
docker push yourname/ai-trading-bot:latest
```

Then update `docker-compose.prod.yml`:
```yaml
image: yourname/ai-trading-bot:v1.0.0
```

---

## CI/CD Automation (Optional)

### Using GitHub Actions

Create `.github/workflows/deploy.yml`:

```yaml
name: Build and Push Docker Image

on:
  push:
    branches: [ main ]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Login to Docker Hub
        uses: docker/login-action@v2
        with:
          username: ${{ secrets.DOCKER_USERNAME }}
          password: ${{ secrets.DOCKER_PASSWORD }}
      
      - name: Build and push
        uses: docker/build-push-action@v4
        with:
          context: .
          push: true
          tags: yourname/ai-trading-bot:latest
```

Add secrets in GitHub: Settings → Secrets → Actions:
- `DOCKER_USERNAME`
- `DOCKER_PASSWORD`

Now every push to main automatically builds and pushes the image!

---

## Comparison: Docker Hub vs AWS ECR

| Feature | Docker Hub | AWS ECR |
|---------|-----------|---------|
| **Cost** | Free (public), $5/mo (private) | $0.10/GB storage + transfer |
| **Security** | Public or private | Private, IAM-based access |
| **Speed** | Global CDN | Fast within AWS region |
| **Best For** | Open source, small projects | Production AWS deployments |
| **Setup** | Very easy | Requires AWS IAM configuration |

---

## Quick Commands Reference

```bash
# Build image
docker build -t yourname/ai-trading-bot:latest .

# Push to Docker Hub
docker push yourname/ai-trading-bot:latest

# Pull and run on EC2
docker-compose -f docker-compose.prod.yml pull
docker-compose -f docker-compose.prod.yml up -d

# View logs
docker-compose -f docker-compose.prod.yml logs -f

# Stop
docker-compose -f docker-compose.prod.yml down

# Update and restart
docker-compose -f docker-compose.prod.yml pull && docker-compose -f docker-compose.prod.yml up -d
```

---

## Troubleshooting

**Image pull fails on EC2:**
```bash
# For Docker Hub: Login on EC2
docker login

# For ECR: Check IAM role is attached to EC2
aws sts get-caller-identity

# Re-login to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <your-ecr-uri>
```

**Build fails on Windows:**
```powershell
# Clear Docker cache
docker system prune -a

# Rebuild
docker build --no-cache -t yourname/ai-trading-bot:latest .
```

---

**You're now ready to deploy your bot using Docker images!** 🚀

**Recommended:** Start with Docker Hub for simplicity, migrate to ECR for production.
