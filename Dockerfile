FROM quay.io/hummingbird/python:latest-fips-builder AS builder

USER 0

RUN dnf5 install -y gcc gcc-c++ python3-devel make && \
    dnf5 clean all

COPY hermetic/librdkafka /tmp/librdkafka
RUN cd /tmp/librdkafka && \
    ./configure --prefix=/usr --libdir=/usr/lib64 && \
    make && \
    make INSTALL=/usr/bin/install install && \
    ldconfig

COPY src src
COPY pyproject.toml pyproject.toml

RUN python3 -m pip install --use-pep517 .

FROM quay.io/hummingbird/python:latest-fips

COPY --from=builder /usr/lib64/librdkafka* /usr/lib64/
COPY --from=builder /etc/ld.so.cache /etc/ld.so.cache
COPY --from=builder /usr/local/lib/ /usr/local/lib/
COPY --from=builder /usr/local/bin/ /usr/local/bin/

COPY default_map.yaml /opt/app-root/src/default_map.yaml
COPY rhosak_map.yaml /opt/app-root/src/rhosak_map.yaml
COPY licenses/LICENSE /licenses/LICENSE

USER 1001

CMD ["storage_broker_consumer_api"]
