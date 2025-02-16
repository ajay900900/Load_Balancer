from flask import Flask, jsonify, request
import requests
import threading
import time
import os

app = Flask(__name__)

schema = None


def periodic_heart_beat():

    while True:
        shardManager = ShardManager()
        shardNameToServerMap = shardManager.getShardNameToServerMap()

        shardsInServer = {}
        for shardName in shardNameToServerMap:
            serverMap = shardNameToServerMap[shardName]

            serverMap.runPrimaryElection(shardName)

            primaryServerName = serverMap.getPrimaryServerName()

            for server in serverMap.getServersList():
                if server not in shardsInServer.keys():
                    shardsInServer[server] = list()
                shardsInServer[server].append(shardName)

        for server in shardsInServer.keys():
            try:
                res = requests.get(f"http://{server}:5000/heartbeat")
                continue
            except:
                pass

            try:
                res = os.popen(
                    f"sudo docker stop {server} ; sudo docker rm {server} ; sudo docker run --platform linux/x86_64 --name {server} --network pub --network-alias {server} -d ds_server:latest"
                ).read()
                if len(res) == 0:
                    raise

                for shardName in shardsInServer[server]:

                    req_body = {"shard": shardName}

                    serverMap = shardNameToServerMap[shardName]
                    primaryServerName = serverMap.getPrimaryServerName()

                    config_req_body = {
                        "shards": [shardName],
                        "schema": schema,
                    }
                    if primaryServerName is not None:
                        WAL_log = requests.get(
                            f"http://{primaryServerName}:5000/get_wal", json=req_body
                        ).json()
                        config_req_body["logRequests"] = WAL_log["data"]

                    while True:
                        try:
                            res = requests.post(
                                f"http://{server}:5000/config", json=config_req_body
                            )
                            break
                        except Exception as e:
                            print(e)
                            time.sleep(3)
            except:
                print("Error in spawning new server")

        time.sleep(15)


class ServerMap:
    def __init__(self):
        self.primaryServerName = None
        self.serversList = []

    def printIt(self):
        print(f"Primary Server - {self.primaryServerName}", flush=True)
        print("ServerList", flush=True)
        for server in self.serversList:
            print(server, flush=True)

    def addServer(self, serverName):
        self.serversList.append(serverName)

    def removeServer(self, serverName):
        if serverName in self.serversList:
            self.serversList.remove(serverName)

        if serverName == self.primaryServerName:
            self.primaryServerName = None

    def runPrimaryElection(self, shardName):

        try:
            res = requests.get(f"http://{self.primaryServerName}:5000/heartbeat")
            return
        except:
            pass

        if self.primaryServerName != None:
            self.serversList.append(self.primaryServerName)

        wal_count = -2
        new_server_name = None

        for serverName in self.serversList:
            try:
                req_body = {"shard": shardName}

                res = requests.get(
                    f"http://{serverName}:5000/get_wal_count", json=req_body
                )

                res = res.json()

                if res["count"] > wal_count:
                    wal_count = res["count"]
                    new_server_name = serverName
            except:
                pass

        self.primaryServerName = new_server_name
        if new_server_name in self.serversList:
            self.serversList.remove(self.primaryServerName)

    def getPrimaryServerName(self):
        return self.primaryServerName

    def getServersList(self):
        return self.serversList


class ShardManager:

    _instance = None

    def __new__(self):
        if not self._instance:
            self._instance = super(ShardManager, self).__new__(self)
            self.shardNameToServerMap = {}

        return self._instance

    def addServerToShard(self, shardName, serverName):
        if shardName not in self.shardNameToServerMap:
            self.shardNameToServerMap[shardName] = ServerMap()

        self.shardNameToServerMap[shardName].addServer(serverName)

    def getPrimaryServerForShard(self, shardName):
        serverMap = self.shardNameToServerMap[shardName]
        serverMap.runPrimaryElection(shardName)

        return serverMap.getPrimaryServerName()

    def getServersListFromShardName(self, shardName):
        return self.shardNameToServerMap[shardName].getServersList()

    def getShardNameToServerMap(self):
        return self.shardNameToServerMap

    def removeServer(self, serverName):

        for shardName in self.shardNameToServerMap:
            serverMap = self.shardNameToServerMap[shardName]
            serverMap.removeServer(serverName)

    def printIt(self):
        for shardName, serverMap in self.shardNameToServerMap.items():
            serverMap.printIt()


@app.route("/primary-elect", methods=["GET"])
def primary_elect():
    payload = request.json

    shardManager = ShardManager()

    return {
        "primary-elect": shardManager.getPrimaryServerForShard(payload["Shard_id"])
    }, 200


@app.route("/add", methods=["POST"])
def add():
    global schema
    payload = request.json
    shardManager = ShardManager()
    schema = payload["schema"]

    for serverName, shardsList in payload["servers"].items():
        for shardName in shardsList:
            shardManager.addServerToShard(shardName, serverName)
    return {"message": "Successful"}, 200


@app.route("/rm", methods=["DELETE"])
def rm():
    payload = request.json

    shardManager = ShardManager()

    try:
        for serverName in payload["servers"]:
            shardManager.removeServer(serverName)
    except:
        return {"message": "Failure in /rm route of shard-manager"}, 400

    return {"message": "Successful in /rm route of shard-manager"}, 200


@app.route("/write", methods=["POST"])
def write():
    payload = request.json

    shardManager = ShardManager()

    serversList = shardManager.getServersListFromShardName(payload["shard"])

    primaryServerName = shardManager.getPrimaryServerForShard(payload["shard"])

    req_body = {
        "data": payload["data"],
        "followers": serversList,
        "shard": payload["shard"],
    }

    try:
        res = requests.post(f"http://{primaryServerName}:5000/write", json=req_body)
    except Exception as e:
        print(e)

    response = {"message": "Succesfully Inserted data", "status": "Sucessful"}

    return response, 200


@app.route("/update", methods=["PUT"])
def update():
    payload = request.json
    shardManager = ShardManager()

    serversList = shardManager.getServersListFromShardName(payload["shard"])
    primaryServerName = shardManager.getPrimaryServerForShard(payload["shard"])

    req_body = {
        "data": payload["data"],
        "followers": serversList,
        "shard": payload["shard"],
        "Stud_id": payload["Stud_id"],
    }

    try:
        res = requests.put(f"http://{primaryServerName}:5000/update", json=req_body)
    except Exception as e:
        print(e)

    response = {"message": "Succesfully Updated data", "status": "Sucessful"}

    return response, 200


@app.route("/del", methods=["DELETE"])
def delete():
    payload = request.json

    shardManager = ShardManager()

    serversList = shardManager.getServersListFromShardName(payload["shard"])

    primaryServerName = shardManager.getPrimaryServerForShard(payload["shard"])

    req_body = {
        "followers": serversList,
        "shard": payload["shard"],
        "Stud_id": payload["Stud_id"],
    }

    try:
        res = requests.delete(f"http://{primaryServerName}:5000/del", json=req_body)
    except Exception as e:
        print(e)

    response = {"message": "Succesfully Delete data", "status": "Sucessful"}

    return response, 200


@app.before_request
def log_request_info():
    app.logger.debug("Body: %s", request.get_json())


if __name__ == "__main__":

    thread = threading.Thread(target=periodic_heart_beat)
    thread.daemon = True  # Daemonize the thread
    thread.start()

    app.run(host="0.0.0.0", port=5000)
