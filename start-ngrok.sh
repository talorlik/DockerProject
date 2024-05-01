#!/bin/bash

readonly DOCKER_CONTAINER='polybot'

wait_until_container_healthy() {
  local max_retries=3
  local retries=0

  until [ "$(docker inspect --format '{{.State.Health.Status}}' "$DOCKER_CONTAINER")" = 'healthy' ] || [ $retries -eq $max_retries ]
  do
    local container_status="$(docker inspect --format '{{.State.Health.Status}}' "$DOCKER_CONTAINER")"
    echo "Waiting for container $DOCKER_CONTAINER to be 'healthy', current status is '$container_status'. Sleeping for 10 seconds..."
    sleep 10
    ((retries++))
  done

  if [ $retries -eq $max_retries ]; then
    echo "Container $DOCKER_CONTAINER did not become healthy after $max_retries retries."
    exit 1
  fi
}

echo "Waiting for container $DOCKER_CONTAINER to fully start..."

sleep 30

wait_until_container_healthy

echo "$DOCKER_CONTAINER started. Starting Ngrok..."

# Starting ngrok via supervisor. The supervisor config for Ngrok is in: /etc/supervisor/conf.d/ngrok.conf
# The Ngrok config file is in ~/.config/ngrok/ngrok.yml
sudo supervisorctl start ngrok

echo "Ngrok started...."

exit 0