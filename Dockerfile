FROM registry.access.redhat.com/hi/python:3.14-fips-builder@sha256:903d8b997342f0cbedd999da21f69a2ec458a6fe7e438a312d6fe07f8c1c444a AS builder

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

FROM registry.access.redhat.com/hi/python:3.14-fips@sha256:f4200cb51d74c2856dc1253d0a8f843aa3f6c973d5e7683d8913292ad8ce534f

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
