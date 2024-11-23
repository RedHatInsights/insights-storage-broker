from setuptools import find_packages, setup

setup(
    name="insights-storage-broker",
    version="0.1",
    url="https://github.com/redhatinsights/insights-storage-broker",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    install_requires=[
        "prometheus-client==0.7.1",
        "logstash-formatter==0.5.17",
        "boto3==1.28.21",
        "watchtower==3.0.1",
        "confluent-kafka==2.2.0",
        "pyyaml==6.0.1",
        "attrs==18.2.0",
        "app-common-python==0.2.7"
    ],
    extras_require={"test": ["pytest>=5.4.1", "flake8>=3.7.9"]},
    entry_points={"console_scripts": ["storage_broker = storage_broker.app:main"]},
)
