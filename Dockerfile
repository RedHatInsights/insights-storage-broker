FROM registry.access.redhat.com/ubi10/python-312-minimal:latest

WORKDIR /app-root/

RUN microdnf install -y gcc python3-devel && microdnf clean all

COPY src src

COPY pyproject.toml pyproject.toml

COPY default_map.yaml /opt/app-root/src/default_map.yaml
COPY rhosak_map.yaml /opt/app-root/src/rhosak_map.yaml

COPY licenses/LICENSE /licenses/LICENSE

RUN python3 -m pip install --use-pep517 .

USER 1001

CMD ["storage_broker_consumer_api"]
