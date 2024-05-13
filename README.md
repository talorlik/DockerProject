# The Polybot plus Image processing Service: Docker Project [![][autotest_badge]][autotest_workflow]

## Intro

This project expands on the Python [Image processing service](https://github.com/talorlik/ImageProcessingService) by adding image object detection capabilities in the form of a Yolo5 model, running it all in Docker containers with Docker Compose and adding elements such as AWS EC2, AWS S3, AWS ECR and MongoDB.

The build and deploy process are executed automatically with GitHub Actions. The workflow also stops/starts the services with Docker compose.

The containers are:

- `mongo1`, `mongo2`, `mongo3`: MongoDB cluster to store data; comprised of three Mongo containers as a ReplicaSet.
- `mongo-init`: Acts as the initiator of the MongoDB cluster.
- `polybot`: Telegram Bot app which handles the messages.
- `yolo5`: Image object detection container based on the Yolo5 pre-train deep learning model.

## Basic flow

1. The user uploads an image on the Telegram App and puts a caption of `predict`.
2. The Polybot service picks up the message and handles it by instantiating the `ObjectDetectionBot`.
3. The image is then uploaded to S3 and an HTTP call is made to the Yolo5 service.
4. In the Yolo5 service the image is downloaded from S3 and the detection process kicks in.
5. The resulted image is uploaded back to S3 and the summary is save to MongoDB.
6. Once the process succeeds the Polybot service responds back to the user with the image and a readable summary of what was found.

## Directory structure
```console
.
├── LICENSE
├── README.md
├── docker-compose-dev.yaml
├── docker-compose.yaml
├── mongo
│   ├── Dockerfile
│   └── init-script.sh
├── polybot
│   ├── Dockerfile
│   ├── __init__.py
│   ├── photos
│   ├── python
│   │   ├── __init__.py
│   │   ├── bot.py
│   │   ├── bot_utils.py
│   │   ├── flask_app.py
│   │   ├── img_proc.py
│   │   └── requirements.txt
│   ├── uwsgi.ini
│   └── wsgi.py
├── start-ngrok.sh
├── test
│   ├── beatles.jpeg
│   ├── test-compose-project.sh
│   ├── test_concat.py
│   ├── test_rotate.py
│   ├── test_salt_n_pepper.py
│   ├── test_segment.py
│   └── test_telegram_bot.py
└── yolo5
    ├── Dockerfile
    ├── app.py
    ├── requirements.txt
    └── yolo_utils.py
```

## Techincal details

### General notes regarding the Python code

- The code makes use of environment variables and secrets so that those values won't be hard coded.
- I've made use of the OO pattern called `Factory` to instantiate the right Bot for the need, based on the incoming message from the Telegram App.
- The **base Bot** (`telebot.TeleBot`) gets instantiated once hence the webhook only gets created once.
- Each respective bot (`Bot`, `QuoteBot`, `ImageProcessingBot`, `ObjectDetectionBot`) essentially "wraps" the base bot while all extend from `Bot`.
- I've made use of multi-threading protection on the exception handling and the bot object instances used, to allow for multiple users to communicate with the bot at the same time without race conditions between them. I've used the Python `threading` package for this.
- I've implemented logic in the `BotFactory` that will reuse an already existing bot instance of a specific type if it's there so that it won't have to recreate it again as well as to be able to reuse already set global variables from within the respective bot instance.
- I've implemented extensive Exception Handling on all possible fails and also implemented retry mechanism where needed.
- The user get a readable message in case of a failure so that he can then try again.
- I've implemented extensive logging so that important information as well as failures are outputted to the `stdout` (These are then viewable in the docker logs)

### MongoDB Cluster (3 containers in a ReplicaSet)

I've converted these instructions [Deploy MongoDB cluster with Docker](https://www.mongodb.com/compatibility/deploying-a-mongodb-cluster-with-docker) into docker compose format.

In addition to creating the three Mongo containers I've automated the initialization process with the use of a 4th container which runs a bash script (`init-script.sh`) for which I've built a separate Docker image.

The bash script does the following:
1. Initializes the ReplicaSet and waits for an `Ok` status and for the `PRIMARY` Mongo instance to be set.
2. It then creates the `admin` user with which I write to the DB so as NOT to use the default `root` user.
3. Creates the database (`image_predictions`) and collection (`prediction_results`) into which the image detection summary gets saved.
4. Upon success of all the above a file is created in a path (`/init_done/success`) that is accessible via a Docker Volume.

### The `yolo5` microservice

[YoloV5](https://github.com/ultralytics/yolov5) is an object detection AI model.
The one used in this project is a lightweight model that can detect [80 objects](https://github.com/ultralytics/yolov5/blob/master/data/coco128.yaml) while it's running on your old, poor, CPU machine.

It runs as a Python Flask-based webserver, with an endpoint `/predict`, which can be used to predict objects in a given image, as follows:

```text
localhost:8081/predict?imgName=street.jpeg
```

The `imgName` query parameter value (`street.jpeg` in the above example) represents an image name stored in an **S3 bucket**.
The `yolo5` service then downloads the image from the S3 bucket and detects objects in it.

**Example output**

```bash
curl -X POST localhost:8081/predict?imgName=street.jpeg
```

Here is an image and the corresponding results summary:

<img src="https://alonitac.github.io/DevOpsTheHardWay/img/docker_project_street.jpeg" width="60%">

```json
{
    "prediction_id": "9a95126c-f222-4c34-ada0-8686709f6432",
    "original_img_path": "data/images/street.jpeg",
    "predicted_img_path": "static/data/9a95126c-f222-4c34-ada0-8686709f6432/street.jpeg",
    "labels": [
      {
        "class": "person",
        "cx": 0.0770833,
        "cy": 0.673675,
        "height": 0.0603291,
        "width": 0.0145833
      },
      {
        "class": "traffic light",
        "cx": 0.134375,
        "cy": 0.577697,
        "height": 0.0329068,
        "width": 0.0104167
      },
      {
        "class": "potted plant",
        "cx": 0.984375,
        "cy": 0.778793,
        "height": 0.095064,
        "width": 0.03125
      },
      {
        "class": "stop sign",
        "cx": 0.159896,
        "cy": 0.481718,
        "height": 0.0859232,
        "width": 0.053125
      },
      {
        "class": "car",
        "cx": 0.130208,
        "cy": 0.734918,
        "height": 0.201097,
        "width": 0.108333
      },
      {
        "class": "bus",
        "cx": 0.285417,
        "cy": 0.675503,
        "height": 0.140768,
        "width": 0.0729167
      }
    ],
    "time": 1692016473.2343626
}
```

The model detected a _person_, _traffic light_, _potted plant_, _stop sign_, _car_, and a _bus_. Try it yourself with different images.

### The `polybot` microservice

The `polybot` handles all the incoming messages from the Telegram Bot and based on either the text sent or the caption added to an image it executes the respective action, be it an image filter or calling the yolo5 service for image object detection.

It is a Python Flask application which I run with uWSGI server to handle load balancing.

The Dockerfile is built as a multi-stage image. It creates a VENV inside and installs all the Python dependencies and then runs the uWSGI server with a custom configuration file (`uwsgi.ini`)

Here is an end-to-end example of how it may look like:

<img src="https://alonitac.github.io/DevOpsTheHardWay/img/docker_project_polysample.jpg" width="30%">

For further details on the **Telegram Bot** and integration with **Ngrok**, you can read [here](https://github.com/talorlik/ImageProcessingService?tab=readme-ov-file#telegram-bot)

### Docker Compose breakdown

The `docker-compose.yaml` file is as follows:
1. There are three Mongo services (`mongo1`, `mongo2`, `mongo3`) sharing the same Docker network (`mongo-cluster`), and run as ReplicaSet.
  a. The MongoDB data is persisted in a Docker volume. Each container has its own (`mongo1_data`, `mongo2_data`, `mongo3_data`).
  b. Internally all MongoDBs run on the same port (`27017`) but externally each container exposes it's own (`27017`, `27018`, `27019` respectively) so that there won't be a clash between them.
2. `mongo-init` container that does the Mongo initialization and "dies" once done (explanation on the bash script it mentioned above).
  a. The MongoDB password is pulled in from Docker secrets (`mongo_db_password`) and is used in the user creation as well as in the `yolo5` service to establish a DB Connection.
3. `yolo5` service shares a separate Docker network (`backend-network`) with the primary Mongo service which is the `mongo1`
  a. In the command to run the container I've implemented a `wait and retry` mechanism so that it won't try to connect to the Mongo before it's full ready and initialized.
  b. It also makes use of the Docker secrets to get the MongoDB password (`mongo_db_password`)
4. `polybot` service shares yet another Docker network with the `yolo5` service (`frontend-network`)
  a. I've implemented a `healthcheck` so that the container will "advertise" it's health status which is being used as part of the deployment process

All the environment variables that are being used in the Docker Compose are taken from the `.env` file which gets generated automatically as part of the deployment process.

Here's an example of how the `.env` file looks:

```text
# .env file

POLYBOT_IMG_NAME=polybot:v123
YOLO5_IMG_NAME=yolo5:v123
TELEGRAM_APP_URL=https://f176-2a06-c701-4cdc-a500-49d5-ae2b-1cd1-61d1.ngrok-free.app
```

Here's how you use it in the compose file:

```yaml
# docker-compose.yaml

services:
  polybot:
    image: ${POLYBOT_IMG_NAME}
```

### AWS preparations
- A `t3.medium` EC2 machine was created in `us-east-1` region in the AWS default VPC and default public subnet.
- A security group was created (`talo-sg`) and attached to the machine. It exposes ports 80, 8080 for external communication, 22 for SSH and lastly ping
- On the EC2 machine I've installed the following:
  - AWS Cli - the cli is not configured so that my credentials will NOT be on the machine.
  - Docker / Docker Compose
  - Python / Pip
  - Ngrok and then configured
  - Supervisor and then configured
- An S3 bucket (`talo-s3`) was created with a folder called `images`
- An ECR repository (`talo-docker-images`) was created in `us-east-1` region into which all 3 docker images are pushed
- An IAM Role (`talo-ec2-role`) with a policy (`talo-ec2-policy`) attached to it was created.
  - The policy follows the `least privilege` principle and only grants the absolute necessary permissions i.e. to List, Put and Get from the S3 bucket only on the `images` folder, to receive authentication token from the ECR and only pull from the specific repo.
  - The role is then attached to the EC2 machine

### CI/CD

The CI/CD is done automatically via GitHub Actions. The workflows (`service-deploy.yaml`, `project_auto_testing.yaml`) makes use of Repository Secrets for the AWS Access Key and Secret, the EC2 SSH private key as well as the Telegram Token and MongoDB password.

Once the code is pushed to the `main` branch a GitHub Action kicks in and the following process begins:
1. First runs the `service-deploy.yaml` workflow
2. In the `setup` job it automatically fetches the EC2 Public IP (as it changes every time the machine starts again) and outputs it.
3. In the `MongoInitBuild` job it builds the `mongo-init` image and pushes it to the pre-created ECR repository (`talo-docker-images`)
4. In the `PolybotBuild` job it builds the `polibot` image and pushes it to the pre-created ECR repository (`talo-docker-images`)
5. In the `Yolo5Build` job it builds the `yolo5` image and pushes it to the pre-created ECR repository (`talo-docker-images`)
6. All the above 4 jobs run in parallel
7. Once those are done successfully, the `Deploy` job kicks in and it does as follows:
  a. It makes use of the `ec2_ip` from the `setup` job to SSH into the EC2 machine
  b. It copies the `docker-compose.yaml` and `start-ngrok.sh`
  c. It makes sure `jq` is installed
  d. Changes to the `PolybotService` directory
  e. Makes the `start-ngrok.sh` executable
  f. Writes the Telegram Token and MongoDB password into their respective files (these are the files that are used in the docker-compose.yaml to create the Docker secrets)
  g. Generates the `.env` file partially from variables and partly from hard-coded values. This is what the docker-compose.yaml file makes use of for the dynamic values
  h. Refreshes the `supervisor` service and uses it to stop the (possibly) already running `ngrok` service
  i. Stops all the containers and removes them with `docker compose down`
  j. Cleans all the Docker volumes which were created
  k. Logs in to ECR
  l. Restarts all the containers in detached mode with `docker compose up -d`
  m. Executes the `start-ngrok.sh` bash script which runs Ngrok via supervisor
8. After the first one is done the second workflow (`project_auto_testing.yaml`) starts and runs the tests

**NOTES:**
1. I've resolved the automation of starting Ngrok via the GitHub Action by using supervisor which was pre-installed on the EC2 machine and configured to run the Ngrok as a background service so that it won't hold up the terminal.
2. In the `start-ngrok.sh` bash script I've written a `wait-until` mechanism so that Ngrok won't start until the `polibot` service is `healthy` hence the `healthcheck` mentioned above.
