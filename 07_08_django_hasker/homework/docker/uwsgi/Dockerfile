FROM python:3.7.3-stretch

COPY files /

RUN cd /var/hasker && \
    pip install pipenv && \
    pipenv install --system

WORKDIR /var/hasker