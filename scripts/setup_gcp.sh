#!/bin/bash
set -e

# ==========================================
# StoryProof GCP Setup Script
# Ubuntu 22.04 LTS / e2-standard-2 (8GB)
# ==========================================

APP_USER=$(whoami)
APP_DIR="/home/$APP_USER/StoryProof"
VENV_DIR="$APP_DIR/venv"

echo ">>> Setting up for user: $APP_USER"
echo ">>> App directory: $APP_DIR"

echo ">>> Updating system..."
sudo DEBIAN_FRONTEND=noninteractive apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get upgrade -y

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

echo ">>> Installing PyTorch (CPU only)..."
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
sudo chown -R $APP_USER:$APP_USER /var/log/storyproof

echo ">>> Configuring Supervisor..."
sudo tee /etc/supervisor/conf.d/storyproof.conf > /dev/null << SUPERVISOR_EOF
[program:storyproof-backend]
directory=$APP_DIR
command=$VENV_DIR/bin/gunicorn -w 1 -k uvicorn.workers.UvicornWorker backend.main:app --bind 0.0.0.0:8000 --timeout 120
user=$APP_USER
autostart=true
autorestart=true
stopsignal=TERM
stopwaitsecs=30
environment=PYTHONUNBUFFERED="1",ENABLE_RERANKER="True"
stderr_logfile=/var/log/storyproof/backend.err.log
stdout_logfile=/var/log/storyproof/backend.out.log

[program:storyproof-celery]
directory=$APP_DIR
command=$VENV_DIR/bin/celery -A backend.worker.celery_app worker --loglevel=info --concurrency=1
user=$APP_USER
autostart=true
autorestart=true
stopsignal=TERM
stopwaitsecs=30
environment=PYTHONUNBUFFERED="1",ENABLE_RERANKER="True"
stderr_logfile=/var/log/storyproof/celery.err.log
stdout_logfile=/var/log/storyproof/celery.out.log
SUPERVISOR_EOF

sudo supervisorctl reread
sudo supervisorctl update

echo ">>> Configuring Nginx..."
sudo tee /etc/nginx/sites-available/storyproof > /dev/null << NGINX_EOF
server {
    listen 80;
    server_name _;

    location / {
        root $APP_DIR/frontend/build;
        index index.html index.htm;
        try_files \$uri \$uri/ /index.html;
    }

    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location /static {
        proxy_pass http://localhost:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }
}
NGINX_EOF

sudo ln -sf /etc/nginx/sites-available/storyproof /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo chmod o+x /home/$APP_USER

sudo nginx -t && sudo systemctl restart nginx

echo ""
echo "========================================="
echo ">>> Setup Complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo "1. .env 파일이 $APP_DIR/.env 에 있는지 확인"
echo "2. Run migrations: cd $APP_DIR && source venv/bin/activate && alembic upgrade head"
echo "3. Build frontend: cd $APP_DIR/frontend && npm install && npm run build"
echo "4. Set permissions: sudo chmod -R o+rx $APP_DIR/frontend/build"
echo "5. Start services: sudo supervisorctl start all"
