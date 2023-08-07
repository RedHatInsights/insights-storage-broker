FROM registry.access.redhat.com/ubi8/ubi-minimal

WORKDIR /app-root/

RUN microdnf install -y python310 python3-devel curl python3-pip

COPY src src

COPY poetry.lock poetry.lock

COPY pyproject.toml pyproject.toml

COPY default_map.yaml /opt/app-root/src/default_map.yaml
COPY rhosak_map.yaml /opt/app-root/src/rhosak_map.yaml

RUN pip3 install --upgrade pip && pip3 install .

CMD ["storage_broker_consumer_api"]
