#!/bin/bash
set -e

# ==========================================
# StoryProof EC2 Setup Script
# Ubuntu 22.04 LTS
# ==========================================

APP_DIR="/home/ubuntu/StoryProof"
VENV_DIR="$APP_DIR/venv"
USER="ubuntu"
DB_NAME="storyproof"
DB_USER="storyproof"
DB_PASS="storyproof_password"

echo ">>> Updating system..."
sudo apt-get update
sudo apt-get upgrade -y

echo ">>> Installing Node.js (LTS)..."
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs

echo ">>> Installing dependencies..."
sudo apt-get install -y python3-pip python3-venv python3-dev libpq-dev postgresql postgresql-contrib redis-server nginx supervisor git build-essential


echo ">>> Configuring PostgreSQL..."
# Check if user exists, if not create
if ! sudo -u postgres psql -t -c '\du' | cut -d \| -f 1 | grep -qw "$DB_USER"; then
    sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASS';"
    echo "Created database user: $DB_USER"
else
    echo "Database user $DB_USER already exists."
fi

# Check if db exists, if not create
if ! sudo -u postgres psql -lqt | cut -d \| -f 1 | grep -qw "$DB_NAME"; then
    sudo -u postgres psql -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;"
    echo "Created database: $DB_NAME"
else
    echo "Database $DB_NAME already exists."
fi

echo ">>> Setting up Python Virtual Environment..."
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
    echo "Virtual environment created at $VENV_DIR"
fi

echo ">>> Installing Python requirements..."
source "$VENV_DIR/bin/activate"
pip install --upgrade pip
pip install gunicorn
if [ -f "$APP_DIR/requirements.txt" ]; then
    pip install -r "$APP_DIR/requirements.txt"
else
    echo "WARNING: requirements.txt not found!"
fi

echo ">>> Configuring Supervisor..."
sudo tee /etc/supervisor/conf.d/storyproof.conf > /dev/null <<EOF
[program:storyproof-backend]
directory=$APP_DIR
command=$VENV_DIR/bin/gunicorn -w 4 -k uvicorn.workers.UvicornWorker backend.main:app --bind 0.0.0.0:8000
user=$USER
autostart=true
autorestart=true
stderr_logfile=/var/log/storyproof/backend.err.log
stdout_logfile=/var/log/storyproof/backend.out.log

[program:storyproof-celery]
directory=$APP_DIR
command=$VENV_DIR/bin/celery -A backend.celery_worker.celery_app worker --loglevel=info
user=$USER
autostart=true
autorestart=true
stderr_logfile=/var/log/storyproof/celery.err.log
stdout_logfile=/var/log/storyproof/celery.out.log
EOF

# Create log directory
sudo mkdir -p /var/log/storyproof
sudo chown -R $USER:$USER /var/log/storyproof

sudo supervisorctl reread
sudo supervisorctl update

echo ">>> Configuring Nginx..."
# Frontend build should be done before this or manually.
# Serving frontend from frontend/dist (assuming build is run)

sudo tee /etc/nginx/sites-available/storyproof > /dev/null <<EOF
server {
    listen 80;
    server_name _;

    location / {
        root $APP_DIR/frontend/dist;
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
}
EOF

sudo ln -sf /etc/nginx/sites-available/storyproof /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx

echo ">>> Setup Complete!"
echo "Please make sure .env file exists in $APP_DIR with correct DATABASE_URL: postgresql://$DB_USER:$DB_PASS@localhost/$DB_NAME"
echo "You may need to run 'npm run build' in frontend directory manually if not included in deploy script."
