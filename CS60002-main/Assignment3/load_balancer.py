from flask import Flask, jsonify, request
import uuid
import requests
import os
import time
import threading

app = Flask(__name__)


def generate_random_id():
    unique_id = uuid.uuid4()
    return int(unique_id.int)


class MultiLockDict:
    _instance = None

    def __new__(self):
        if not self._instance:
            self._instance = super(MultiLockDict, self).__new__(self)
            self.lock_dict = {}
            self.global_lock = threading.Lock()

        return self._instance

    def acquire_lock(self, key):
        with self.global_lock:
            if key not in self.lock_dict:
                self.lock_dict[key] = threading.Lock()
        self.lock_dict[key].acquire()

    def release_lock(self, key):
        self.lock_dict[key].release()


class Server:

    shardsToDB = {}
    shards = []
    server_id = -1

    def __init__(self, id, server_name):
        self.server_id = id
        self.shardsToDB = {}
        self.shards = []
        self.server_name = server_name

    def addShard(self, shard_id, shard_name):
        self.shardsToDB[shard_id] = shard_name
        if shard_id not in self.shards:
            self.shards.append(shard_id)

    def updateData(self, shard_id, data):
        payload = {
            "shard": self.shardsToDB[shard_id],
            "Stud_id": data["Stud_id"],
            "data": data,
        }
        res = requests.put(f"http://{self.server_name}:5000/update", json=payload)

    def delData(self, shard_id, stud_id):
        payload = {
            "shard": self.shardsToDB[shard_id],
            "Stud_id": stud_id,
        }
        res = requests.delete(f"http://{self.server_name}:5000/del", json=payload)

    def insertData(self, shard_id, data):
        payload = {
            "shard": self.shardsToDB[shard_id],
            "data": data,
        }
        res = requests.post(f"http://{self.server_name}:5000/write", json=payload)

    def getData(self, shard_id, id_limits):
        payload = {
            "shard": self.shardsToDB[shard_id],
            "Stud_id": id_limits,
        }
        res = requests.get(f"http://{self.server_name}:5000/read", json=payload)
        return res.json()["data"]

    def getStatus(self):
        res = []
        for key in self.shardsToDB:
            res.append(key)

        return res

    def __str__(self):
        res = f"server_id - {self.server_id}\n"

        for key, value in self.shardsToDB.items():
            res += f"{key} - {value}\n"
        res += "]\n"
        return res


class ServerMap:

    _instance = None

    nameToIdMap = {}
    idToNameMap = {}
    idToServer = {}

    def __new__(self):
        if not self._instance:
            self._instance = super(ServerMap, self).__new__(self)
            self.nameToIdMap = {}
            self.idToNameMap = {}
            self.idToServer = {}

        return self._instance

    def getServersCount(self):
        return len(self.nameToIdMap)

    def addServer(self, server_name):
        unique_id = generate_random_id()
        self.nameToIdMap[server_name] = unique_id
        self.idToNameMap[unique_id] = server_name
        self.idToServer[unique_id] = Server(unique_id, server_name)

    def addShardToServer(self, server_id, shard_id, shard_name):
        server = self.idToServer[server_id]
        server.addShard(shard_id, shard_name)

    def removeServer(self, server_id):
        try:
            server = self.idToServer[server_id]
            server_name = self.idToNameMap[server_id]

            res = os.popen(
                f"sudo docker stop {server_name} && sudo docker rm {server_name}"
            ).read()

            if len(res) == 0:
                raise Exception("<ERROR> Container could not be stopped!")

            shardList = []
            for shard in server.shardsToDB.keys():
                shardList.append(shard)

            self.idToServer.pop(server_id)
            self.idToNameMap.pop(server_id)
            self.nameToIdMap.pop(server_name)

            return shardList
        except Exception as e:
            raise e

    def getIdFromName(self, server_name):
        return self.nameToIdMap[server_name]

    def getNameFromId(self, server_id):
        return self.idToNameMap[server_id]

    def getData(self, shardFragment, id_limits):

        server = self.idToServer[shardFragment["server_id"]]

        return server.getData(shardFragment["shard_id"], id_limits)

    def getStatus(self, server_id=None):

        if server_id is not None:
            return self.idToServer[server_id].getStatus()

        else:
            res = {}

            for key, value in self.nameToIdMap.items():
                res[key] = self.idToServer[value].getStatus()

            return res

    def insertBulkData(self, serversList, shard_id, data):
        for server_id in serversList:
            server = self.idToServer[server_id]
            server.insertData(shard_id, data)

    def updateData(self, serversList, shard_id, data):
        for server_id in serversList:
            server = self.idToServer[server_id]
            server.updateData(shard_id, data)

    def delData(self, serversList, shard_id, stud_id):
        for server_id in serversList:
            server = self.idToServer[server_id]
            server.delData(shard_id, stud_id)

    def __str__(self):
        res = "NameToIDMap - [ \n "

        for key, value in self.nameToIdMap.items():
            res += f"{key} - {value} \n"

        res += "]\n"

        res += "IDToServer - [\n"

        for key, value in self.idToServer.items():
            res += f"{key} - {value.__str__()}\n"

        res += "]\n"
        return res


class Shard:

    shard_id = -1
    student_id_low = -1
    shard_size = 0

    RING_SIZE = 512
    VIRTUAL_INSTANCE = 9

    hashRing = []

    def __init__(self, shard_id, student_id_low, shard_size):
        self.shard_id = shard_id
        self.student_id_low = student_id_low
        self.shard_size = shard_size
        self.hashRing = [-1 for _ in range(self.RING_SIZE)]

    def isDataPresent(self, id_limits):
        id_low = self.student_id_low
        id_high = self.student_id_low + self.shard_size - 1

        if id_low > id_limits["high"] or id_high < id_limits["low"]:
            return False

        return True

    def getStudentIdLow(self):
        return self.student_id_low

    def getShardSize(self):
        return self.shard_size

    def request_hash(self, i):
        return (i**2 + 2 * i + 17) % self.RING_SIZE

    def virtual_server_hash(self, i, j):
        return (i**2 + j**2 + 2 * j + 25) % self.RING_SIZE

    def vacantRingSpot(self, virtual_hash):
        while self.hashRing[virtual_hash] >= 0:
            virtual_hash += 1
            virtual_hash %= self.RING_SIZE

        return virtual_hash

    def addServer(self, server_id):
        for loop in range(0, self.VIRTUAL_INSTANCE):
            virtual_hash = self.virtual_server_hash(server_id, loop + 1)
            emptyRingSpot = self.vacantRingSpot(virtual_hash)
            self.hashRing[emptyRingSpot] = server_id

    def getLoadBalancedServerId(self, request_id):
        mapped_index = request_id % self.RING_SIZE
        st_index = mapped_index

        while True:
            if self.hashRing[mapped_index] < 0:
                mapped_index += 1
                mapped_index %= self.RING_SIZE
            else:
                return self.hashRing[mapped_index]

            if mapped_index == st_index:
                break

        return -1

    def removeServer(self, server_id):
        for idx in range(len(self.hashRing)):
            if self.hashRing[idx] == server_id:
                self.hashRing[idx] = -1

        if self.hashRing.count(-1) == len(self.hashRing):
            return False
        return True

    def getAllServers(self):

        serversDict = {}
        for server_id in self.hashRing:
            if server_id >= 0:
                serversDict[server_id] = 1

        return list(serversDict.keys())

    def __str__(self):
        return f"shard_id - {self.shard_id} \n student_id_low - {self.student_id_low} \n shard_size - {self.shard_size}"


class ShardMap:

    _instance = None

    nameToIdMap = {}
    idToShard = {}

    def __new__(self):
        if not self._instance:
            self._instance = super(ShardMap, self).__new__(self)
            self.nameToIdMap = {}
            self.idToShard = {}

        return self._instance

    def getLoadBalancedServerForShard(self, shard_name):
        shard_id = self.nameToIdMap[shard_name]
        request_id = generate_random_id()
        return self.idToShard[shard_id].getLoadBalancedServerId(request_id)

    def getIdFromName(self, shard_name):
        return self.nameToIdMap[shard_name]

    def getAllServersFromShardId(self, shard_id):
        return self.idToShard[shard_id].getAllServers()

    def getShardIdFromStudId(self, student_id):

        for shard_id, shard in self.idToShard.items():
            id_limits = {"low": student_id, "high": student_id}

            if shard.isDataPresent(id_limits):
                return shard_id

    def getNameFromId(self, shard_id):

        for key, value in self.nameToIdMap.items():
            if shard_id == value:
                return key

        return "NA Shard"

    def addShard(self, shard):
        shard_name = shard["Shard_id"]
        student_id_low = shard["Stud_id_low"]
        shard_size = shard["Shard_size"]

        if shard_name not in self.nameToIdMap:
            unique_id = generate_random_id()
            self.nameToIdMap[shard_name] = unique_id
            self.idToShard[unique_id] = Shard(unique_id, student_id_low, shard_size)

    def addServerToShard(self, shard_name, server_id):
        shard_id = self.nameToIdMap[shard_name]
        shard = self.idToShard[shard_id]

        shard.addServer(server_id)

    def removeServerFromShard(self, shardList, server_id):
        for shard_id in shardList:
            shard = self.idToShard[shard_id]

            res = shard.removeServer(server_id)
            if not res:
                shard_name = self.getNameFromId(shard_id)
                self.nameToIdMap.pop(shard_name)
                self.idToShard.pop(shard_id)

    def getStatus(self):

        res = []
        for key, value in self.nameToIdMap.items():

            currRes = {
                "Shard_id": key,
                "Stud_id_low": self.idToShard[value].getStudentIdLow(),
                "Shard_size": self.idToShard[value].getShardSize(),
            }

            res.append(currRes)

        return res

    def getShardFragments(self, id_limits):

        shardFragments = []

        for shard_id, shard in self.idToShard.items():
            if shard.isDataPresent(id_limits):
                request_id = generate_random_id()

                shardFragment = {
                    "shard_id": shard_id,
                    "server_id": shard.getLoadBalancedServerId(request_id),
                }
                shardFragments.append(shardFragment)

        return shardFragments

    def __str__(self):
        res = "NameToID - [\n "

        for key, value in self.nameToIdMap.items():
            res += f"{key} - {value},\n "
        res += " ] \n"

        res += "IDToShard - [ \n"

        for key, value in self.idToShard.items():
            res += f"{key} - {value.__str__()}, \n"

        res += " ] \n"

        return res


schema = None


@app.route("/init", methods=["POST"])
def init():
    payload = request.json

    shardMap = ShardMap()
    serverMap = ServerMap()

    global schema
    schema = payload["schema"]

    for shard in payload["shards"]:
        shardMap.addShard(shard)

    for server_name, shards in payload["servers"].items():
        try:
            res = os.popen(
                f"sudo docker run --platform linux/x86_64 --name {server_name} --network pub --network-alias {server_name} -d ds_server:latest"
            ).read()

            if len(res) == 0:
                raise
        except Exception as e:
            print(e)

    for server_name, shards in payload["servers"].items():
        try:
            serverMap.addServer(server_name)
            server_id = serverMap.getIdFromName(server_name)

            shard_ids = []
            for shard in shards:
                shardMap.addServerToShard(shard, server_id)
                shard_id = shardMap.getIdFromName(shard)
                serverMap.addShardToServer(server_id, shard_id, shard)
                shard_ids.append(shard)

            req_body = {"schema": schema, "shards": shard_ids}
            while True:
                try:
                    res = requests.post(
                        f"http://{server_name}:5000/config", json=req_body
                    )
                    break
                except Exception as e:
                    print(e)
                    time.sleep(3)

        except Exception as e:
            print(e)

    sm_payload = {}
    sm_payload["servers"] = payload["servers"]
    sm_payload["schema"] = schema
    try:
        res = requests.post("http://shard_manager_1:5000/add", json=sm_payload)
    except Exception as e:
        print(e)

    response = {"message": "Configured Database", "status": "success"}

    return response, 200


@app.route("/status", methods=["GET"])
def status():

    serverMap = ServerMap()
    shardMap = ShardMap()

    shards = shardMap.getStatus()
    servers = serverMap.getStatus()

    newServers = {}

    for key, value in servers.items():
        shardNames = []
        for shardId in value:
            shardNames.append(shardMap.getNameFromId(shardId))

        newServers[key] = shardNames

    response = {"shards": shards, "servers": newServers}

    return response, 200


@app.route("/add", methods=["POST"])
def add():
    try:
        payload = request.json

        serverMap = ServerMap()
        shardMap = ShardMap()

        if payload["n"] > len(payload["servers"]):
            raise Exception(
                "<Error> Number of new servers (n) is greater than newly added instances"
            )

        for shard in payload["new_shards"]:
            shardMap.addShard(shard)

        addedServerNames = []
        sm_payload_servers_dict = {}

        for server_name, shards in payload["servers"].items():
            try:
                if "[" in server_name:
                    server_name = f"Server{generate_random_id()%10000}"

                sm_payload_servers_dict[server_name] = shards
                serverMap.addServer(server_name)
                addedServerNames.append(server_name)
                server_id = serverMap.getIdFromName(server_name)

                for shard in shards:
                    shardMap.addServerToShard(shard, server_id)
                    shard_id = shardMap.getIdFromName(shard)
                    serverMap.addShardToServer(server_id, shard_id, shard)

            except Exception as e:
                print(e)

        sm_payload = {}
        sm_payload["servers"] = sm_payload_servers_dict
        sm_payload["schema"] = schema
        try:
            res = requests.post("http://shard_manager_1:5000/add", json=sm_payload)
        except Exception as e:
            print(e)

        response = {}

        response["N"] = serverMap.getServersCount()

        message = "Added "
        for server in addedServerNames:
            message += f"{server}, "
        message += "successfully"

        response["message"] = message
        response["status"] = "successful"

        return response, 200
    except Exception as e:
        response = {"message": str(e), "status": "failure"}

        return response, 400


@app.route("/rm", methods=["DELETE"])
def remove():
    try:
        payload = request.json

        serverMap = ServerMap()
        shardMap = ShardMap()
        if payload["n"] < len(payload["servers"]):
            raise Exception(
                "<ERROR> Number of server names should be less than or equal to the number of instances to be removed"
            )

        serversToDel = []
        serversToDelNames = []

        for serverName, serverId in serverMap.nameToIdMap.items():
            if serverName in payload["servers"]:
                serversToDel.append(serverId)
                serversToDelNames.append(serverName)

        for serverName, serverId in serverMap.nameToIdMap.items():
            if len(serversToDel) == payload["n"]:
                break

            if serverName not in serversToDel:
                serversToDel.append(serverId)
                serversToDelNames.append(serverName)

        sm_payload = {}
        sm_payload["servers"] = serversToDelNames
        try:
            res = requests.delete("http://shard_manager_1:5000/rm", json=sm_payload)
        except Exception as e:
            raise e

        for serverId in serversToDel:
            shardList = serverMap.removeServer(serverId)
            shardMap.removeServerFromShard(shardList, serverId)

        response = {
            "message": {"N": payload["n"], "servers": serversToDelNames},
            "status": "successful",
        }
        return jsonify(response), 200

    except Exception as e:
        response = {"message": str(e), "status": "failure"}
        return jsonify(response), 400


@app.route("/read", methods=["GET"])
def read():
    payload = request.json
    studId = payload["Stud_id"]

    shardMap = ShardMap()
    serverMap = ServerMap()

    shardFragments = shardMap.getShardFragments(studId)
    result = []
    for shardFragment in shardFragments:
        server_id = shardFragment["server_id"]
        server_name = serverMap.getNameFromId(server_id)

        shardFragment["server_id"] = serverMap.getIdFromName(server_name)
        data = serverMap.getData(shardFragment, studId)
        for _ in data:
            _.pop("id")
            result.append(_)

    response = {"shards_queried": [], "data": result, "status": "success"}

    for shardFragment in shardFragments:
        response["shards_queried"].append(
            shardMap.getNameFromId(shardFragment["shard_id"])
        )

    return response, 200


@app.route("/read/<serverName>", methods=["GET"])
def readServer(serverName):
    response = {}
    res = requests.get("http://localhost:5000/status").json()

    serversList = res["servers"].keys()
    if serverName not in serversList:
        response["message"] = "Requested server does not exist"
        response["status"] = "failure"
        return response, 400

    shard_limits = {}
    for shardData in res["shards"]:
        shard_limits[shardData["Shard_id"]] = {
            "low": shardData["Stud_id_low"],
            "high": shardData["Stud_id_low"] + shardData["Shard_size"] - 1,
        }

    shardsOnServer = res["servers"][serverName]

    response = {}

    for shard in shardsOnServer:
        shardPayload = {"shard": shard, "Stud_id": shard_limits[shard]}
        try:
            res = requests.get(
                f"http://{serverName}:5000/read", json=shardPayload
            ).json()
            response[shard] = []
            for _ in res["data"]:
                _.pop("id")
                response[shard].append(_)
        except Exception as e:
            response["message"] = str(e)
            response["status"] = "failure"
            return response, 500

    response["status"] = "success"
    return response, 200


@app.route("/write", methods=["POST"])
def write():
    payload = request.json

    shardWiseData = {}

    shardMap = ShardMap()

    for data in payload["data"]:
        shard_id = shardMap.getShardIdFromStudId(data["Stud_id"])

        if shard_id not in shardWiseData:
            shardWiseData[shard_id] = [data]
        else:
            shardWiseData[shard_id].append(data)

    multi_lock_dict = MultiLockDict()

    for shard_id, data in shardWiseData.items():

        multi_lock_dict.acquire_lock(shard_id)

        try:
            shardName = shardMap.getNameFromId(shard_id)

            req_payload = {"shard": shardName, "data": data}

            res = requests.post(f"http://shard_manager_1:5000/write", json=req_payload)

        except Exception as e:
            return {
                "message": str(e),
                "status": "failure",
            }, 400
        finally:
            multi_lock_dict.release_lock(shard_id)

    response = {
        "message": f"{len(payload['data'])} Data entries added",
        "status": "success",
    }

    return response, 200


@app.route("/update", methods=["PUT"])
def update():
    try:
        payload = request.json

        if payload["Stud_id"] != payload["data"]["Stud_id"]:
            raise Exception("<ERROR> Student ID does not match!")

        shardMap = ShardMap()

        shard_id = shardMap.getShardIdFromStudId(payload["Stud_id"])

        multi_lock_dict = MultiLockDict()

        multi_lock_dict.acquire_lock(shard_id)

        try:
            shardName = shardMap.getNameFromId(shard_id)
            req_payload = {
                "data": payload["data"],
                "shard": shardName,
                "Stud_id": payload["Stud_id"],
            }

            res = requests.put(f"http://shard_manager_1:5000/update", json=req_payload)

        except Exception as e:
            return {
                "message": str(e),
                "status": "failure",
            }, 400
        finally:
            multi_lock_dict.release_lock(shard_id)

        response = {
            "message": f"Data entry for Stud_id - {payload['Stud_id']} updated",
            "status": "success",
        }
        return response, 200
    except Exception as e:
        response = {"message": str(e), "status": "failure"}
        return response, 400


@app.route("/del", methods=["DELETE"])
def delete():
    payload = request.json

    shardMap = ShardMap()

    shard_id = shardMap.getShardIdFromStudId(payload["Stud_id"])

    multi_lock_dict = MultiLockDict()
    multi_lock_dict.acquire_lock(shard_id)

    try:
        shardName = shardMap.getNameFromId(shard_id)

        req_payload = {"shard": shardName, "Stud_id": payload["Stud_id"]}

        res = requests.delete(f"http://shard_manager_1:5000/del", json=req_payload)

    except Exception as e:
        return {
            "message": str(e),
            "status": "failure",
        }, 400
    finally:
        multi_lock_dict.release_lock(shard_id)

    response = {
        "message": f"Data entry for Stud_id - {payload['Stud_id']} removed from all replicas",
        "status": "success",
    }

    return response, 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
