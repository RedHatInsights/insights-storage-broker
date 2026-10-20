FROM registry.access.redhat.com/hi/python:latest-fips-builder@sha256:c6c27abe3470084affe30f1d4e2899eda5efe1a323df3f4f58642b9e23e47188 AS builder

USER 0

RUN dnf5 install -y gcc gcc-c++ python3-devel make \
    openssl-devel cyrus-sasl-devel libxcrypt && \
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

FROM registry.access.redhat.com/hi/python:latest-fips@sha256:58e5ca571852d89f65a06a9ae55afdef651650b788a9116245469b14d2309def

COPY --from=builder /usr/lib64/librdkafka* /usr/lib64/
COPY --from=builder /usr/lib64/libsasl2* /usr/lib64/
COPY --from=builder /usr/lib64/libcrypt* /usr/lib64/
COPY --from=builder /etc/ld.so.cache /etc/ld.so.cache
COPY --from=builder /usr/local/lib/ /usr/local/lib/
COPY --from=builder /usr/local/lib64/ /usr/local/lib64/
COPY --from=builder /usr/local/bin/ /usr/local/bin/

COPY default_map.yaml /opt/app-root/src/default_map.yaml
COPY rhosak_map.yaml /opt/app-root/src/rhosak_map.yaml
COPY licenses/LICENSE /licenses/LICENSE

USER 1001

CMD ["storage_broker_consumer_api"]
