FROM registry.access.redhat.com/ubi10/python-312-minimal:latest

WORKDIR /app-root/

USER 0

COPY hermetic/confluent-archive.key /tmp/confluent-archive.key
RUN rpm --import /tmp/confluent-archive.key && \
    microdnf install -y gcc python3-devel && \
    microdnf install -y librdkafka-devel || true && \
    microdnf clean all && \
    rm -f /tmp/confluent-archive.key

COPY src src

COPY pyproject.toml pyproject.toml

COPY default_map.yaml /opt/app-root/src/default_map.yaml
COPY rhosak_map.yaml /opt/app-root/src/rhosak_map.yaml

COPY licenses/LICENSE /licenses/LICENSE

RUN python3 -m pip install --use-pep517 .

USER 1001

CMD ["storage_broker_consumer_api"]
