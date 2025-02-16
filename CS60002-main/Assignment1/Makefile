.PHONY: all

all:
    
	docker build -t ds_server:latest ./server
	docker compose up -d

clean:
	docker compose down --rmi all
	docker stop $$(docker ps -a -q)
	docker rm $$(docker ps -a -q)
	docker image rm ds_server:latest