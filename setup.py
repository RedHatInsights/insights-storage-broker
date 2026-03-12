from setuptools import find_packages, setup

setup(
    name="insights-storage-broker",
    version="0.1",
    url="https://github.com/redhatinsights/insights-storage-broker",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    install_requires=[
        "prometheus-client==0.24.1",
        "logstash-formatter==0.5.17",
        "watchtower==3.4.0",
        "confluent-kafka==2.11.0",
        "boto3==1.39.4",
        "pyyaml==6.0.2",
        "attrs==25.3.0",
        "app-common-python==0.2.8"
    ],
    extras_require={"test": ["pytest>=8.0.0", "flake8>=7.3.0"]},
    entry_points={"console_scripts": ["storage_broker = storage_broker.app:main"]},
)
