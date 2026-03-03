@echo off
echo Pulling latest changes...
git pull

echo Building Docker image...
docker build -t collapsebot-tg/sigma .

echo Stop and remove old container...
docker stop collapsebot-tg
docker rm collapsebot-tg

echo running new container...
docker run -d --name collapsebot-tg collapsebot-tg/sigma

echo Registration or bot start successful!
pause
