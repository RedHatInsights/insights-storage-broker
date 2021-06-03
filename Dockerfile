FROM registry.redhat.io/ubi8/ubi-minimal
WORKDIR /opt/app-root/
RUN microdnf install -y python36 python3-devel
COPY src src
COPY poetry.lock poetry.lock
COPY pyproject.toml pyproject.toml
COPY default_map.yaml /opt/app-root/src/default_map.yaml
RUN pip3 install --upgrade pip && pip3 install .
RUN curl -L -o /usr/bin/haberdasher \
    https://github.com/RedHatInsights/haberdasher/releases/latest/download/haberdasher_linux_amd64 && \
    chmod 755 /usr/bin/haberdasher
ENTRYPOINT ["/usr/bin/haberdasher"]
CMD ["storage_broker"]
