docker kill --signal=SIGTERM master
docker stop trademan
docker rm trademan
docker image rm traderscafe/trademan:latest