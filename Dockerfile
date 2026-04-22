FROM registry.access.redhat.com/ubi10/python-312-minimal:latest AS builder

WORKDIR /app-root/

USER 0

RUN microdnf install -y gcc gcc-c++ python3-devel make && \
    microdnf clean all

COPY hermetic/librdkafka /tmp/librdkafka
RUN cd /tmp/librdkafka && \
    ./configure --prefix=/usr && \
    make && \
    make INSTALL=/usr/bin/install install && \
    ldconfig

COPY src src
COPY pyproject.toml pyproject.toml

RUN python3 -m pip install --use-pep517 .

FROM registry.access.redhat.com/ubi10/python-312-minimal:latest

WORKDIR /app-root/

USER 0

COPY --from=builder /usr/lib64/librdkafka* /usr/lib64/
RUN ldconfig

COPY --from=builder /opt/app-root/ /opt/app-root/

COPY default_map.yaml /opt/app-root/src/default_map.yaml
COPY rhosak_map.yaml /opt/app-root/src/rhosak_map.yaml
COPY licenses/LICENSE /licenses/LICENSE

USER 1001

CMD ["storage_broker_consumer_api"]
