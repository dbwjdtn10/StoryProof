#!/bin/bash
set -e

# ==========================================
# StoryProof EC2 Setup Script
# Ubuntu 22.04 LTS / t3.small
# ==========================================

APP_DIR="/home/ubuntu/StoryProof"
VENV_DIR="$APP_DIR/venv"
USER="ubuntu"

echo ">>> Updating system..."
sudo DEBIAN_FRONTEND=noninteractive apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get upgrade -y

echo ">>> Configuring Swap (2GB)..."
if [ ! -f /swapfile ]; then
    sudo fallocate -l 2G /swapfile
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile
    sudo swapon /swapfile
    echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
    echo "Swap created and enabled."
else
    echo "Swap file already exists, skipping."
fi

echo ">>> Installing Node.js (LTS)..."
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y nodejs

echo ">>> Installing system dependencies..."
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
    python3-pip python3-venv python3-dev libpq-dev \
    postgresql postgresql-contrib redis-server \
    nginx supervisor git build-essential

echo ">>> Configuring PostgreSQL..."
sudo systemctl start postgresql

# postgres 유저 비밀번호 설정 및 DB 생성
sudo -u postgres psql << 'PSQL_EOF'
ALTER USER postgres PASSWORD '1234!@#$';
PSQL_EOF

if ! sudo -u postgres psql -lqt | cut -d \| -f 1 | grep -qw "StoryProof"; then
    sudo -u postgres psql -c 'CREATE DATABASE "StoryProof";'
    echo "Created database: StoryProof"
else
    echo "Database StoryProof already exists."
fi

echo ">>> Setting up Python Virtual Environment..."
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
    echo "Virtual environment created at $VENV_DIR"
fi

echo ">>> Installing PyTorch (CPU only - saves ~2GB)..."
source "$VENV_DIR/bin/activate"
pip install --upgrade pip
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip cache purge

echo ">>> Installing Python requirements..."
pip install gunicorn
if [ -f "$APP_DIR/requirements.txt" ]; then
    pip install -r "$APP_DIR/requirements.txt"
else
    echo "WARNING: requirements.txt not found!"
fi

echo ">>> Fixing pinecone package..."
pip uninstall pinecone-client -y 2>/dev/null || true
pip install pinecone

echo ">>> Installing extra dependencies..."
pip install 'pydantic[email]' python-multipart

echo ">>> Creating log directory..."
sudo mkdir -p /var/log/storyproof
sudo chown -R $USER:$USER /var/log/storyproof

echo ">>> Configuring Supervisor..."
sudo cp "$APP_DIR/scripts/storyproof.conf" /etc/supervisor/conf.d/storyproof.conf
sudo supervisorctl reread
sudo supervisorctl update

echo ">>> Configuring Nginx..."
sudo tee /etc/nginx/sites-available/storyproof > /dev/null << 'NGINX_EOF'
server {
    listen 80;
    server_name _;

    location / {
        root /home/ubuntu/StoryProof/frontend/build;
        index index.html index.htm;
        try_files $uri $uri/ /index.html;
    }

    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
NGINX_EOF

sudo ln -sf /etc/nginx/sites-available/storyproof /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo chmod o+x /home/ubuntu

sudo nginx -t && sudo systemctl restart nginx

echo ">>> Setup Complete!"
echo ""
echo "Next steps:"
echo "1. Upload .env file: scp .env ubuntu@SERVER_IP:~/StoryProof/.env"
echo "2. Run migrations: cd ~/StoryProof && source venv/bin/activate && alembic upgrade head"
echo "3. Build frontend: cd ~/StoryProof/frontend && npm install && npm run build"
echo "4. Set frontend permissions: sudo chmod -R o+rx /home/ubuntu/StoryProof/frontend/build"
echo "5. Start services: sudo supervisorctl start all"
