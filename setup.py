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
        "boto3==1.12.38",
        "watchtower==0.7.3",
        "confluent-kafka==1.5.0",
        "pyyaml==5.3.1",
        "attrs==18.2.0",
        "app-common-python"
    ],
    extras_require={"test": ["pytest>=5.4.1", "flake8>=3.7.9"]},
    entry_points={"console_scripts": ["storage_broker = storage_broker.app:main"]},
)
