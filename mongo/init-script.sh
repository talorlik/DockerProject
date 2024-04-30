#!/bin/bash

echo 'Waiting for MongoDB instances to become available...'
# List all MongoDB hosts
hosts=("mongo1:27017" "mongo2:27017" "mongo3:27017")

# Function to check MongoDB connectivity
wait_for_mongo() {
    local host=$1
    local max_attempts=10
    local attempt=1
    while true; do
        if mongosh --host $host --eval "db.runCommand({ ping: 1 })"; then
            echo "$host is ready!"
            break
        else
            echo "Waiting for $host to be ready..."
            sleep 10
        fi
        if (( attempt++ == max_attempts )); then
            echo "Failed to connect to $host after $max_attempts attempts."
            exit 1
        fi
    done
}

# Wait for all MongoDB instances to become available
for host in "${hosts[@]}"; do
  wait_for_mongo "$host"
done

echo 'All MongoDB instances are available. Initializing the replica set and creating a user, db, and collection...'

# Initiate the replica set
mongosh --host mongo1:27017 --eval "
  console.log('Start: initiating the replica set...');

  rs.initiate({
    _id: 'mongo-replica-set',
    members: [
      {_id: 0, host: 'mongo1:27017'},
      {_id: 1, host: 'mongo2:27017'},
      {_id: 2, host: 'mongo3:27017'}
    ]
  });

  // Wait until the replica set is fully initialized
  while (true) {
    const status = rs.status();
    if (status.ok == 1 && status.members.filter(m => m.stateStr == 'PRIMARY').length > 0) break;
    sleep(1000);
  }

  console.log('End: replica set initialized.');
"

sleep 10

# Create the admin user
mongosh --host mongo1:27017 --eval "
  console.log('Start: creating admin user...');
  const db = db.getSiblingDB('admin');
  const pwd = JSON.parse(JSON.stringify('$(cat /var/run/secrets/mongo_db_password)'));
  db.createUser({
    user: 'admin',
    pwd: pwd,
    mechanisms: ['SCRAM-SHA-1'],
    roles: [
      { role: 'root', db: 'admin' },
      { role: 'clusterAdmin', db: 'admin' },
      { role: 'dbOwner', db: 'admin' },
      { role: 'readWriteAnyDatabase', db: 'admin'}
    ]
  });
  console.log('End: admin user created successfully.');
"

sleep 5

# Create the specific database and collection
mongosh --host mongo1:27017 --eval "
  console.log('Start: creating image db and collection...');
  const imgDb = db.getSiblingDB('image_predictions');
  imgDb.createCollection('prediction_results');
  console.log('End: database and collection created successfully.');
"

sleep 5

touch /init_done/success

echo 'MongoDB cluster setup complete.'
