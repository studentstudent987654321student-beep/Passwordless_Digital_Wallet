# Deployment Guide
## Passwordless Digital Wallet

This guide covers deploying the Passwordless Digital Wallet in various environments.

---

## Table of Contents

1. [Local Development](#local-development)
2. [Docker Deployment](#docker-deployment)
3. [Production Deployment](#production-deployment)
4. [Cloud Deployment (AWS/Azure)](#cloud-deployment)
5. [Troubleshooting](#troubleshooting)

---

## Local Development

### Prerequisites

- Python 3.11+
- PostgreSQL 14+
- Redis 7+
- Node.js 18+ (for frontend tools)

### Setup Steps

1. **Create Virtual Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/macOS
   .\venv\Scripts\activate   # Windows
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

4. **Initialize Database**
   ```bash
   flask db init
   flask db migrate -m "Initial migration"
   flask db upgrade
   ```

5. **Generate SSL Certificates**
   ```bash
   # Linux/macOS
   ./scripts/generate_ssl.sh
   
   # Windows
   .\scripts\generate_ssl.ps1
   ```

6. **Run Development Server**
   ```bash
   flask run --cert=nginx/certs/server.crt --key=nginx/certs/server.key
   ```

---

## Docker Deployment

### Prerequisites

- Docker Desktop 4.x
- Docker Compose v2.x

### Quick Start

```bash
# Build and start all services
docker-compose up --build

# Run in background
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Stop and remove volumes (caution: deletes data)
docker-compose down -v
```

### Service Architecture

```
                    ┌─────────────┐
                    │   Nginx     │ :443 (HTTPS)
                    │   Proxy     │ :80 (redirect)
                    └─────┬───────┘
                          │
                    ┌─────▼───────┐
                    │   Flask     │ :5000
                    │   App       │
                    └───┬─────┬───┘
                        │     │
          ┌─────────────▼┐   ┌▼─────────────┐
          │  PostgreSQL  │   │    Redis     │
          │     DB       │   │   Cache      │
          │    :5432     │   │    :6379     │
          └──────────────┘   └──────────────┘
```

### Container Details

| Service | Image | Ports | Purpose |
|---------|-------|-------|---------|
| web | Custom (Dockerfile) | 5000 | Flask application |
| db | postgres:16-alpine | 5432 | Database |
| redis | redis:7-alpine | 6379 | Sessions/Cache |
| nginx | nginx:alpine | 80, 443 | Reverse proxy |

### Scaling

```bash
# Scale Flask workers
docker-compose up -d --scale web=3
```

---

## Production Deployment

### Security Checklist

- [ ] Use strong `SECRET_KEY` (minimum 32 bytes)
- [ ] Enable `HTTPS` only mode
- [ ] Configure firewall (allow only 80, 443)
- [ ] Use Let's Encrypt for SSL
- [ ] Set `FLASK_ENV=production`
- [ ] Enable rate limiting
- [ ] Configure log rotation
- [ ] Set up monitoring/alerting
- [ ] Regular security updates
- [ ] Database backups configured

### Let's Encrypt SSL

```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot certonly --webroot \
    -w /var/www/html \
    -d yourdomain.com \
    -d www.yourdomain.com

# Auto-renewal
sudo crontab -e
# Add: 0 3 * * * certbot renew --quiet
```

### Nginx Production Config

```nginx
# /etc/nginx/sites-available/wallet

upstream flask_app {
    server 127.0.0.1:5000;
    keepalive 32;
}

server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    location / {
        proxy_pass http://flask_app;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Connection "";
    }

    location /static/ {
        alias /var/www/wallet/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
```

### Gunicorn Production

```bash
# Install gunicorn
pip install gunicorn

# Run with workers
gunicorn -w 4 -b 127.0.0.1:5000 \
    --access-logfile /var/log/wallet/access.log \
    --error-logfile /var/log/wallet/error.log \
    "app.main:create_app()"
```

### Systemd Service

```ini
# /etc/systemd/system/wallet.service
[Unit]
Description=Passwordless Wallet
After=network.target postgresql.service redis.service

[Service]
User=wallet
Group=www-data
WorkingDirectory=/var/www/wallet
Environment="PATH=/var/www/wallet/venv/bin"
EnvironmentFile=/var/www/wallet/.env
ExecStart=/var/www/wallet/venv/bin/gunicorn \
    -w 4 -b 127.0.0.1:5000 \
    --access-logfile /var/log/wallet/access.log \
    --error-logfile /var/log/wallet/error.log \
    "app.main:create_app()"
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start
sudo systemctl enable wallet
sudo systemctl start wallet
sudo systemctl status wallet
```

---

## Cloud Deployment

### AWS Deployment

#### Architecture

```
                    ┌─────────────────┐
                    │   CloudFront    │
                    │     (CDN)       │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  Application    │
                    │  Load Balancer  │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
       ┌──────▼──────┐┌──────▼──────┐┌──────▼──────┐
       │  ECS Task   ││  ECS Task   ││  ECS Task   │
       │  (Flask)    ││  (Flask)    ││  (Flask)    │
       └──────┬──────┘└──────┬──────┘└──────┬──────┘
              │              │              │
              └──────────────┼──────────────┘
                             │
              ┌──────────────┼──────────────┐
              │                             │
       ┌──────▼──────┐              ┌───────▼──────┐
       │    RDS      │              │  ElastiCache │
       │ PostgreSQL  │              │    Redis     │
       └─────────────┘              └──────────────┘
```

#### ECR/ECS Deployment

```bash
# Build and push to ECR
aws ecr get-login-password | docker login --username AWS --password-stdin <account>.dkr.ecr.<region>.amazonaws.com
docker build -t wallet .
docker tag wallet:latest <account>.dkr.ecr.<region>.amazonaws.com/wallet:latest
docker push <account>.dkr.ecr.<region>.amazonaws.com/wallet:latest

# Create ECS task definition and service via AWS Console or CloudFormation
```

### Azure Deployment

#### Architecture

- Azure Container Instances or App Service
- Azure Database for PostgreSQL
- Azure Cache for Redis
- Azure Application Gateway

```bash
# Deploy to Azure Container Instances
az container create \
    --resource-group wallet-rg \
    --name wallet-app \
    --image <acr>.azurecr.io/wallet:latest \
    --dns-name-label wallet-app \
    --ports 5000 \
    --environment-variables \
        FLASK_ENV=production \
        DATABASE_URL="<azure-postgres-url>" \
        REDIS_URL="<azure-redis-url>"
```

---

## Database Operations

### Backup

```bash
# PostgreSQL backup
pg_dump -h localhost -U wallet wallet_db > backup_$(date +%Y%m%d).sql

# Docker backup
docker-compose exec db pg_dump -U wallet wallet_db > backup.sql
```

### Restore

```bash
# Restore from backup
psql -h localhost -U wallet wallet_db < backup.sql

# Docker restore
docker-compose exec -T db psql -U wallet wallet_db < backup.sql
```

### Migrations

```bash
# Create new migration
flask db migrate -m "Description"

# Apply migrations
flask db upgrade

# Rollback
flask db downgrade
```

---

## Monitoring

### Health Check Endpoint

Add to your application:

```python
@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy',
        'database': check_db(),
        'redis': check_redis(),
        'timestamp': datetime.utcnow().isoformat()
    })
```

### Prometheus Metrics

```bash
pip install prometheus-flask-exporter
```

### Log Aggregation

Configure JSON logging for easy parsing:

```python
import logging
import json

class JSONFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps({
            'timestamp': record.created,
            'level': record.levelname,
            'message': record.getMessage(),
            'module': record.module
        })
```

---

## Troubleshooting

### Common Issues

#### WebAuthn Not Working

1. **Not on HTTPS**: WebAuthn requires secure context
2. **Invalid RP ID**: Must match the domain
3. **Browser compatibility**: Use modern browser
4. **Authenticator issue**: Check device biometrics

#### Database Connection Failed

```bash
# Check PostgreSQL is running
docker-compose ps
docker-compose logs db

# Check connection
docker-compose exec db psql -U wallet -d wallet_db
```

#### Redis Connection Failed

```bash
# Check Redis is running
docker-compose exec redis redis-cli ping

# Check connection
docker-compose exec redis redis-cli info
```

#### SSL Certificate Issues

```bash
# Regenerate certificates
rm -rf nginx/certs/*
./scripts/generate_ssl.sh

# Rebuild nginx
docker-compose up -d --build nginx
```

### Debug Mode

```bash
# Enable debug logging
export FLASK_DEBUG=1
export LOG_LEVEL=DEBUG

# Check application logs
docker-compose logs -f web
```

---

## Performance Tuning

### Database

```sql
-- PostgreSQL tuning (postgresql.conf)
shared_buffers = 256MB
effective_cache_size = 768MB
work_mem = 16MB
maintenance_work_mem = 128MB
```

### Redis

```conf
# redis.conf
maxmemory 256mb
maxmemory-policy allkeys-lru
```

### Flask/Gunicorn

```bash
# Calculate workers: (2 x CPU cores) + 1
gunicorn -w 9 -k gevent --worker-connections 1000 \
    --timeout 30 --keep-alive 5 \
    "app.main:create_app()"
```

---

## Support

For issues and questions:
- Check logs: `docker-compose logs -f`
- Review documentation
- Create GitHub issue with logs and environment details
