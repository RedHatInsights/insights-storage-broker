FROM registry.access.redhat.com/hi/python:latest-fips-builder@sha256:b0ddbf5851c28159ca3b160915dd88cb7efdd47b630f8af4ef892c9ed28c8573 AS builder

USER 0

# Install system dependencies
RUN dnf5 install -y gcc gcc-c++ python3-devel make \
    openssl-devel cyrus-sasl-devel libxcrypt && \
    dnf5 clean all

# Build librdkafka
COPY hermetic/librdkafka /tmp/librdkafka
RUN cd /tmp/librdkafka && \
    ./configure --prefix=/usr --libdir=/usr/lib64 && \
    make && \
    make INSTALL=/usr/bin/install install && \
    ldconfig

# Install uv (option 1: from pip)
RUN python3 -m pip install uv

# Copy source and dependencies
COPY src src
COPY pyproject.toml pyproject.toml

# Test 1: Install with uv directly (no lock file)
RUN uv pip install --system .

FROM registry.access.redhat.com/hi/python:latest-fips@sha256:b42659de8901e25e1de3c040ce3673b88f63df323036ea68cb9c2c209db66424

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
