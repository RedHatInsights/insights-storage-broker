
FROM registry.redhat.io/ubi8/python-36
USER 0
RUN yum install -y git && yum remove -y nodejs npm kernel-headers && yum update -y && yum clean all
COPY src src
COPY poetry.lock .
COPY pyproject.toml .
RUN pip3 install --upgrade pip && pip3 install .
USER 1001
ENTRYPOINT ["storage_broker"]