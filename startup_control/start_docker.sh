# write a docker script that starts a master container
#!/bin/bash

# Set variables
CONTAINER_NAME="master-container"
IMAGE_NAME="master-image:latest"
PORT_MAPPING="8000:8000"

docker build -t master-image:latest . 
# Check if the container already exists
if [ "$(docker ps -aq -f name=$CONTAINER_NAME)" ]; then
    echo "Container $CONTAINER_NAME already exists. Stopping and removing..."
    docker stop $CONTAINER_NAME
    docker rm $CONTAINER_NAME
fi

# Check if the image exists locally
if [[ "$(docker images -q $IMAGE_NAME 2> /dev/null)" == "" ]]; then
    echo "Image $IMAGE_NAME does not exist locally. Please build it first."
    echo "You can build it using: docker build -t $IMAGE_NAME ."
    exit 1
fi

# Run the master container
echo "Starting master container..."
docker run -d \
    --name $CONTAINER_NAME \
    -p $PORT_MAPPING \
    --restart unless-stopped \
    $IMAGE_NAME

# Check if the container started successfully
if [ "$(docker ps -q -f name=$CONTAINER_NAME)" ]; then
    echo "Master container started successfully."
else
    echo "Failed to start master container. Check logs for details."
    exit 1
fi

# Run the container logs
docker logs -f $CONTAINER_NAME
