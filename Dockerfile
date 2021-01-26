FROM registry.redhat.io/ubi8/python-36

USER 0

RUN REMOVE_PKGS="npm nodejs kernel-headers" && \
    yum remove -y $REMOVE_PKGS && \
    yum clean all

COPY src src

COPY poetry.lock poetry.lock

COPY pyproject.toml pyproject.toml

COPY default_map.yaml /opt/app-root/src/default_map.yaml

RUN pip3 install --upgrade pip && pip3 install .

USER 1001

ENTRYPOINT ["storage_broker"]
