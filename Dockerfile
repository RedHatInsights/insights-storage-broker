# FROM registry.access.redhat.com/ubi8/ubi-minimal:latest
FROM quay.io/hummingbird/python:latest-builder

WORKDIR /app-root/

USER 0

RUN INSTALL_PKGS="python3.11 python3.11-devel curl" && \
    dnf --nodocs -y upgrade && \
    dnf -y --setopt=tsflags=nodocs --setopt=install_weak_deps=0 install $INSTALL_PKGS && \
    rpm -V $INSTALL_PKGS && \
    dnf -y clean all --enablerepo='*'

COPY src src

COPY poetry.lock poetry.lock

COPY pyproject.toml pyproject.toml

COPY default_map.yaml /opt/app-root/src/default_map.yaml
COPY rhosak_map.yaml /opt/app-root/src/rhosak_map.yaml

COPY licenses/LICENSE /licenses/LICENSE

RUN python3.11 -m ensurepip && python3.11 -m pip install .

USER 1001

CMD ["storage_broker_consumer_api"]
