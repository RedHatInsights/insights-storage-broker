FROM registry.access.redhat.com/hi/python:latest-fips-builder@sha256:b022774c169f050ddc8a8cb459ec4e790a29c245cd868378acd5011be9805559 AS builder

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

FROM registry.access.redhat.com/hi/python:latest-fips@sha256:37aa583c7c1919eb8e1cc2f1446579db222efee7623ca79f52c72c2d126ee277

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
