#!/bin/bash
# Deployment script for Telegram Music Bot
# This script deploys the latest code to the server

SERVER_IP="140.245.56.100"
SERVER_USER="root"
SERVER_PASS="Akshay343402355468"
SERVER_PORT="22"
REPO_URL="https://github.com/nishkarshk212/Telegram_music"
BOT_DIR="/root/Telegram_music"

echo "=== Deploying Telegram Music Bot to $SERVER_IP ==="

# First, make sure we have sshpass installed
if ! command -v sshpass &> /dev/null
then
    echo "sshpass not found, installing..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        brew install sshpass
    else
        sudo apt-get install -y sshpass
    fi
fi

echo "Step 1: Connecting to server and updating code..."
sshpass -p "$SERVER_PASS" ssh -o StrictHostKeyChecking=no -p $SERVER_PORT $SERVER_USER@$SERVER_IP << EOF
    echo "Connected to server successfully"
    
    # Navigate to bot directory
    if [ -d "$BOT_DIR" ]; then
        cd "$BOT_DIR"
        echo "Updating existing repository..."
        git fetch origin
        git reset --hard origin/main
        git pull origin main
    else
        echo "Cloning repository for first time..."
        git clone "$REPO_URL" "$BOT_DIR"
        cd "$BOT_DIR"
    fi
    
    echo "Step 2: Installing dependencies..."
    pip3 install -U -r requirements.txt
    
    echo "Step 3: Checking logs before restart..."
    if [ -f "bot.log" ]; then
        echo "=== Last 50 lines of bot.log ==="
        tail -50 bot.log
    fi
    
    echo "Step 4: Restarting the bot..."
    # Kill any running bot processes (adjust as needed)
    pkill -f "python3 -m AloneX" || true
    pkill -f "bash start" || true
    
    # Wait a bit for processes to terminate
    sleep 3
    
    # Start the bot
    echo "Starting bot in background..."
    nohup bash start > bot.log 2>&1 &
    echo "Bot started successfully! Check bot.log for output"
    
    echo "Step 5: Waiting for bot to start..."
    sleep 5
    
    echo "=== First 20 lines of new bot.log ==="
    head -20 bot.log
EOF

echo "=== Deployment completed! ==="
