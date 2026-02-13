#!/bin/bash
set -e

# ==========================================
# StoryProof EC2 Deployment Script
# Usage: ./scripts/deploy_ec2.sh
# ==========================================

APP_DIR="/home/ubuntu/StoryProof"
VENV_DIR="$APP_DIR/venv"

echo ">>> Starting Deployment..."
echo "Target Directory: $APP_DIR"

# 1. Update Code
echo ">>> Pulling latest changes from git..."
cd $APP_DIR
# Reset any local changes to ensure clean pull (optional, be careful)
# git reset --hard HEAD
git pull origin main

# 2. Backend Setup
echo ">>> Updating Backend..."
source "$VENV_DIR/bin/activate"

echo "Installing Python dependencies..."
pip install -r requirements.txt

echo "Running Database Migrations..."
# Alembic should pick up .env from current directory via Pydantic or env.py
alembic upgrade head

# 3. Frontend Setup
echo ">>> Updating Frontend..."
cd "$APP_DIR/frontend"

echo "Installing Node dependencies..."
npm install

echo "Building Frontend..."
npm run build

# 4. Restart Services
echo ">>> Restarting Services..."
sudo supervisorctl restart storyproof-backend
sudo supervisorctl restart storyproof-celery
sudo systemctl reload nginx

echo ">>> Deployment Successfully Completed!"
echo "Check status with: sudo supervisorctl status"
