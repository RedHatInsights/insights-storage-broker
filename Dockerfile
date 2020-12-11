FROM registry.redhat.io/ubi8/python-36
COPY src src
COPY poetry.lock .
COPY pyproject.toml .
COPY default_map.yaml .
RUN pip3 install --upgrade pip setuptools && pip3 install .
USER 0
RUN yum remove -y npm nodejs kernel-headers && yum update -y && yum clean all
USER 1001
ENTRYPOINT ["storage_broker"]
