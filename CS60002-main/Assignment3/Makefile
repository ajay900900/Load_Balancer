.PHONY: all

all:
    
	docker build -t ds_server:latest ./server --platform linux/x86_64
	docker compose up -d

clean:
	docker compose down --rmi all
	docker stop $$(docker ps -a -q)
	docker rm $$(docker ps -a -q)
	docker network rm pub
	docker image rm ds_server:latest

restart:
	make clean ; make all