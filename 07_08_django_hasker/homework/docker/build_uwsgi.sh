#!/usr/bin/env sh

cd "$(dirname "$0")"

FILES_DIR="./uwsgi/files/var/hasker/"
IMAGE_NAME="hasker_uwsgi"
DOCKER_FILE="./uwsgi/"

cp ./../hasker/Pipfile ${FILES_DIR}
cp ./../hasker/Pipfile.lock ${FILES_DIR}
docker build --tag ${IMAGE_NAME} ${DOCKER_FILE}

