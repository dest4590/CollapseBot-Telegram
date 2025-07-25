git pull
docker stop collapsebob-tg
docker remove collapsebob-tg
docker build -t collapse/bot-tg .
docker run -d --name collapsebob-tg --restart always -v collapse_bot_config:/app/config collapse/bot-tg
