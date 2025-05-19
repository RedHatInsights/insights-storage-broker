from setuptools import find_packages, setup

setup(
    name="insights-storage-broker",
    version="0.1",
    url="https://github.com/redhatinsights/insights-storage-broker",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    install_requires=[
        "prometheus-client==0.21.1",
        "logstash-formatter==0.5.17",
        "watchtower==3.4.0",
        "confluent-kafka==2.10.0",
        "boto3==1.38.18",
        "pyyaml==6.0.2",
        "attrs==18.2.0",
        "app-common-python==0.2.3"
    ],
    extras_require={"test": ["pytest>=5.4.1", "flake8>=3.7.9"]},
    entry_points={"console_scripts": ["storage_broker = storage_broker.app:main"]},
)
