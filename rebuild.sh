git pull
docker stop collapsebob-tg
docker remove collapsebob-tg
docker build -t collapse/bot-tg .
docker run -d --name collapsebob-tg --restart always collapse/bot-tg
