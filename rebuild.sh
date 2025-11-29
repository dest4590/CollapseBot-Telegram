git pull
docker build --tag=collapsebob-tg/sigma .
docker kill collapsebob-tg
docker rm collapsebob-tg
docker run -d --name collapsebob-tg collapsebob-tg/sigma