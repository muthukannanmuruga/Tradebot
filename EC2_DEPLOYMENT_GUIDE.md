# EC2 Deployment Guide for AI Trading Bot

## Prerequisites
- AWS Account
- EC2 instance (t2.small or larger recommended)
- SSH key pair for EC2 access

---

## Step 1: Launch EC2 Instance

1. **Go to AWS EC2 Console**
   - Select "Launch Instance"

2. **Configure Instance:**
   - **Name:** ai-trading-bot
   - **AMI:** Amazon Linux 2023 or Ubuntu 22.04
   - **Instance Type:** t2.small (or t2.micro for testing)
   - **Key Pair:** Select or create a new key pair (download .pem file)
   - **Storage:** 20 GB gp3

3. **Security Group Settings:**
   - **SSH (Port 22):** Your IP only
   - **Custom TCP (Port 8000):** Your IP (or 0.0.0.0/0 for public access)

4. **Launch Instance**

---

## Step 2: Connect to EC2

```bash
# Windows PowerShell (adjust path to your .pem file)
ssh -i "path/to/your-key.pem" ec2-user@<EC2-PUBLIC-IP>

# If using Ubuntu AMI, use:
ssh -i "path/to/your-key.pem" ubuntu@<EC2-PUBLIC-IP>
```

---

## Step 3: Install Docker on EC2

### For Amazon Linux 2023:
```bash
# Update system
sudo yum update -y

# Install Docker
sudo yum install docker -y

# Start Docker service
sudo systemctl start docker
sudo systemctl enable docker

# Add ec2-user to docker group
sudo usermod -a -G docker ec2-user

# Log out and back in for group changes to take effect
exit
# SSH back in
```

### For Ubuntu:
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
sudo apt install docker.io -y

# Start Docker
sudo systemctl start docker
sudo systemctl enable docker

# Add user to docker group
sudo usermod -a -G docker ubuntu

# Log out and back in
exit
# SSH back in
```

### Install Docker Compose:
```bash
# Download docker-compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose

# Make it executable
sudo chmod +x /usr/local/bin/docker-compose

# Verify installation
docker --version
docker-compose --version
```

---

## Step 4: Transfer Project to EC2

### Option A: Using Git (Recommended)
```bash
# On EC2
git clone <your-repo-url>
cd Tradebot
```

### Option B: Using SCP from Windows
```powershell
# On your Windows machine
scp -i "path/to/your-key.pem" -r E:\Tradebot ec2-user@<EC2-PUBLIC-IP>:~/
```

---

## Step 5: Setup Environment Variables on EC2

```bash
# Navigate to project directory
cd ~/Tradebot

# Create .env file
nano .env
```

**Paste your environment variables:**
```env
# Binance API Keys
BINANCE_API_KEY=your_binance_api_key
BINANCE_API_SECRET=your_binance_secret
BINANCE_TESTNET_API_KEY=your_testnet_api_key
BINANCE_TESTNET_API_SECRET=your_testnet_secret

# DeepSeek API
DEEPSEEK_API_KEY=your_deepseek_api_key

# Database (Neon PostgreSQL)
DATABASE_URL=postgresql://mediumdb_owner:npg_tLr49JysMEbj@ep-sparkling-star-a4d5qdkr-pooler.us-east-1.aws.neon.tech/Tradingbot?sslmode=require&channel_binding=require

# Trading Configuration
BINANCE_TESTNET=True
TRADING_PAIR=BTCUSDT
TRADING_AMOUNT_QUOTE=1
CHECK_INTERVAL_SECONDS=60
MAX_DAILY_TRADES=10
```

**Save and exit:** Press `Ctrl+X`, then `Y`, then `Enter`

---

## Step 6: Build and Run the Container

```bash
# Make sure you're in the project directory
cd ~/Tradebot

# Build and start the container
docker-compose up -d --build

# View logs
docker-compose logs -f

# Check container status
docker ps
```

---

## Step 7: Verify Deployment

### Check if the bot is running:
```bash
# Check container status
docker-compose ps

# View real-time logs
docker-compose logs -f trading-bot

# Test API endpoint
curl http://localhost:8000/

# From your local machine (replace with EC2 public IP)
curl http://<EC2-PUBLIC-IP>:8000/
```

### Access API Documentation:
Open browser: `http://<EC2-PUBLIC-IP>:8000/docs`

---

## Step 8: Useful Commands

```bash
# Stop the container
docker-compose down

# Restart the container
docker-compose restart

# View logs (last 100 lines)
docker-compose logs --tail=100 trading-bot

# Update code and redeploy
git pull
docker-compose up -d --build

# Check container resource usage
docker stats

# Access container shell
docker exec -it ai-trading-bot bash

# Clean up Docker resources
docker system prune -a
```

---

## Step 9: Setup Auto-Start on Reboot

```bash
# Create systemd service file
sudo nano /etc/systemd/system/trading-bot.service
```

**Paste this content:**
```ini
[Unit]
Description=AI Trading Bot
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/ec2-user/Tradebot
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
User=ec2-user

[Install]
WantedBy=multi-user.target
```

**Enable the service:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable trading-bot.service
sudo systemctl start trading-bot.service

# Check status
sudo systemctl status trading-bot.service
```

---

## Step 10: Security Best Practices

### 1. Restrict SSH Access
```bash
# Edit security group in AWS console
# Set SSH (22) source to "My IP" only
```

### 2. Use IAM Roles (Optional)
- Attach IAM role to EC2 for AWS service access
- Avoid hardcoding AWS credentials

### 3. Setup CloudWatch Logs (Optional)
```bash
# Install CloudWatch agent
sudo yum install amazon-cloudwatch-agent -y

# Configure log shipping
sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-config-wizard
```

### 4. Regular Updates
```bash
# Update system regularly
sudo yum update -y

# Update Docker images
docker-compose pull
docker-compose up -d
```

### 5. Backup Strategy
```bash
# Backup .env file securely
# Use AWS Secrets Manager for production
# Backup database (Neon has automatic backups)
```

---

## Monitoring & Troubleshooting

### Check Bot Health
```bash
# Health check endpoint
curl http://localhost:8000/

# View trade history in database
# Access via your PostgreSQL client or Neon dashboard
```

### Common Issues

**Container won't start:**
```bash
# Check logs
docker-compose logs

# Check .env file exists and has correct values
cat .env

# Verify Docker is running
sudo systemctl status docker
```

**Port 8000 not accessible:**
```bash
# Check security group allows port 8000
# Check container is running: docker ps
# Check logs: docker-compose logs
```

**Database connection issues:**
```bash
# Test database connection
docker exec -it ai-trading-bot python -c "from app.database import init_db; init_db(); print('DB OK')"
```

---

## Scaling Considerations

### For Production:
1. **Use AWS ECS/Fargate** instead of single EC2
2. **Load Balancer** for high availability
3. **AWS Secrets Manager** for credentials
4. **CloudWatch** for monitoring and alerts
5. **RDS Aurora** instead of Neon (optional)
6. **Auto Scaling** based on CPU/memory

### Cost Optimization:
- Use **t3/t4g instances** (ARM-based)
- **Reserved Instances** for long-term savings
- **Spot Instances** for non-critical workloads
- Monitor with **AWS Cost Explorer**

---

## Quick Reference

```bash
# Start bot
docker-compose up -d

# Stop bot
docker-compose down

# View logs
docker-compose logs -f

# Restart bot
docker-compose restart

# Update and redeploy
git pull && docker-compose up -d --build

# Access container
docker exec -it ai-trading-bot bash

# Check status
docker-compose ps
```

---

## Support

If you encounter issues:
1. Check logs: `docker-compose logs`
2. Verify .env file configuration
3. Test database connection
4. Check EC2 security group settings
5. Verify Docker is running

---

**Your bot is now running 24/7 on AWS EC2!** 🚀

Access API: `http://<EC2-PUBLIC-IP>:8000/docs`
