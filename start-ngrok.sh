#!/bin/bash

readonly DOCKER_CONTAINER='polybot'

wait_until_container_healthy() {
  local max_retries=10
  local retries=0

  until [ "$(docker inspect --format '{{.State.Health.Status}}' "$DOCKER_CONTAINER")" = 'healthy' ] || [ $retries -eq $max_retries ]
  do
    local container_status="$(docker inspect --format '{{.State.Health.Status}}' "$DOCKER_CONTAINER")"
    echo "Waiting for container $DOCKER_CONTAINER to be 'healthy', current status is '$container_status'. Sleeping for 2 seconds..."
    sleep 10
    ((retries++))
  done

  if [ $retries -eq $max_retries ]; then
    echo "Container $DOCKER_CONTAINER did not become healthy after $max_retries retries."
    exit 1
  fi
}

wait_until_container_healthy

# Make sure to provide the correct path to ngrok if it's not in the default $PATH
ngrok start botapp --log=stdout > /dev/null &