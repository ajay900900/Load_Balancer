# CS60002: Distributed Systems (Spring 2024)

## Distributed Load Balancer with Sharding

This project implements a distributed load balancer using Flask and Python, featuring sharding, leader election, and fault tolerance mechanisms.

### Components

1. **ServerMap** - Maps server IDs to server instances.
2. **Server** - Manages data storage, CRUD operations, and shard metadata.
3. **ShardMap** - Maps shard IDs to shard instances.
4. **Shard** - Implements consistent hashing for load balancing.
5. **ShardManager** - Maintains shard-server mappings and handles leader elections.

### Storage Handling

- **SQLHandler** - Manages database connections and queries.
- **DataHandler** - Provides an abstraction for different database solutions (SQL/NoSQL).
- **Manager** - A service layer for database operations.

### Log Replication

- Write requests go to the primary server, which logs and forwards them to secondaries.
- Secondary servers commit data upon confirmation.
- If a server crashes, logs restore consistency.

### Design Choices

1. **In-Memory Load Balancer** - Faster response times using Python dictionaries.
2. **Two-Stage Locking** - Ensures write consistency with global and shard-level locks.
3. **Server Spawning & Leader Election** - Detects failures, restores state, and elects new leaders.

## Prerequisites

Install the following dependencies:

- **Docker**
- **Docker Compose**
- **GNU Make**

### Installation

Deploy the system:
```sh
make all
```

Shutdown and clean up:
```sh
make clean
```

## Performance Analysis

Tested with 10,000 concurrent requests using different configurations:

| Configuration | Read Speed | Write Speed |
|--------------|------------|------------|
| 6 Servers, 4 Shards, 3 Replicas | 105.31/s | 28.78/s |
| 6 Servers, 4 Shards, 6 Replicas | 138.06/s | 18.63/s |
| 10 Servers, 6 Shards, 8 Replicas | 145.43/s | 16.86/s |

### Observations

- More replicas increase read speed but slow down writes due to locking overhead.
- More servers improve availability and parallel request handling.

