# Insights Storage Broker

The Insights Storage Broker microservice handles interaction between the platform and remote stores for storage of payloads that pass through the platform.

## How it Works

Storage Workflow
![UML](http://www.plantuml.com/plantuml/png/PO_DJiD038JlUOfv0LuW1rHnuumuHywkarhD_iXsAi7Jqx2DIidHCplVpfpCINrD2zwpoNnsmuSNfPdnfkN2sd5syI_OEbfG6JaENgg4hfAw1AcK7TOYmzWYaPn6CeRvhxg62_j3ZMmkcLnAtht_z9VNPsI_Vu5sGpcmNDb0I6osEPEMT3jRk-Vu4PUB9bhacmr-PcpTC1L5rHBOJF9yGFmTqoEKAlVm90l3ImCzjg4zFN2EytjysixQUldDdxSgLuaS8NcpxhWXKUrEdEEQbXy0 "Insights Storage Broker")

Insights Storage Broker can be configured to consume from multiple topics by supplying a configuration file in YAML format with the specified topic, bucket, and formatter for the resulting object in cloud storage.

Example Configuration:

    platform.upload.validation:                                     # topic
      normalizer: Validation                                        # normalizer (to be covered further down)
    platform.upload.buckit:
      normalizer: Openshift
      services:                                                     # list of services
        openshift:                                                  # service (defined by content type)
          format: "{org_id}/{cluster_id}/{timestamp}-{request_id}"  # format of resulting file object
          bucket: "insights-buck-it-openshift"                      # storage bucket
        ansible:
          format: "{org_id}/{cluster_id}/{timestamp}-{request_id}"
          bucket: "insights-buck-it-ansible"

The configuration file allows for new buckets, topics, and formatters to be added to the service without changing the underlying code.

## Support for Validation Messages

Insights Storage Broker consumes from the `platform.upload.validation` topic. Storage broker expects to recieve **all** the data in the message that the validation service originally recieved in addition to the the `validation` key.

If a failure message is recieved, Storage Broker will copy the file to the rejected bucket and not advertise the availability of the payload to the platform.

Validation Workflow:
![UML](http://www.plantuml.com/plantuml/png/hLAxRjmm4Epr5GlMbWzvL48W6EbI94tQ0C8UjISpvaFXBXKSZFnxI4idMxX74KG50N5dPdU6-y22KPApyCMp6Hw5uRk4Y0F1vnYUA5PZhXjjHlG24rhJenW_T4nnCfegycBa2AD5EOJekZJQW7rtGWQ_4U1PkzlFsbV8EA6nkBTKPGdS8rCclj2IVY9vlOtqaxIShi-dgzlhSpN0IMjYtXrojnG9NFx9NIgqCjUeXpS-87_VWX34aXE4muKu6dXMaNubOkbChnfGkDTz_UxzXu_gxeTNhtAbjWoW_XJj6n7MxJQtTVHrvCBVOkhsQgeDO3zH5CFaoByuMMimuh6WBxYzeVVyAMIOyMZ1yG0wUCd2xHse56rn-YWoShFRuM--dr_hFbUoSR9CK1xWF6l_NxDU7laVibwODxD-kvvDzZyUy-4S-aj1Ri7gQvY8Jxc3X6MhOGQe8h2XrErcxPkLMjfMb5i-v2Cv-nS0 "Validation Workflow")

## Normalizers

In order to make Storage Broker more dynamic, it supports the ability for a user to define their own data normalizer to provide the required keys to the service. Normalizers can be found in `normalizers.py` and more can be added
if need be, or a service can choose to use an existing normalizer.

The only requirmeent for Storage Broker to determine which normalizer to use is that the `service` key is available in the root of the JSON being parsed. This is provided by ingress messages by default. Any other keys to be used must be
added as attributes of your normalizer class.

The only **required** keys in a normalizer at this point are `size`, `service`, and `request_id`. Any other keys you establish can be used for formatting the resulting object filename.


## Local Development

### Prerequisites

* Python 3.11
* docker-compose

### Step 1: Spin-up dependencies

```
docker-compose -f compose.yml up
```

### Step 2: Start storage broker

```
pip install .

BOOTSTRAP_SERVERS=localhost:29092 BUCKET_MAP_FILE=default_map.yaml storage_broker
```

#### (Optional) Start the storage broker API

```
storage_broker_api
```

### Step 3: Produce a sample validation message

```
make produce_validation_message
```

### Local AWS S3 interaction testing using Minio

You can test the AWS interaction of storage broker using Minio.
To do so, you will need to set the following environment variables to the storage broker consumer or API.

```
S3_ENDPOINT_URL=<minio_api_endpoint/>
AWS_ACCESS_KEY_ID=<minio_access_key_id/>
AWS_SECRET_ACCESS_KEY=<minio_secret_access_key/>
STAGE_BUCKET=<bucket_name/>
```

For example
```
AWS_ACCESS_KEY_ID=$MINIO_ACCESS_KEY AWS_SECRET_ACCESS_KEY=$MINIO_SECRET_KEY S3_ENDPOINT_URL=minio_api_endpoint:9000 STAGE_BUCKET=insights-dev-upload-perm storage_brokerer_api
```

Local Minio access keys are provided [here](https://github.com/RedHatInsights/insights-storage-broker/blob/master/.env).

## Updating dependencies

### Updating base image dependencies

We are currently using the [ubi8/ubi-minimal](https://catalog.redhat.com/software/containers/ubi8/ubi-minimal/5c359a62bed8bd75a2c3fba8?architecture=amd64&image=65bba3c874ca1a2ae9885926) base image.
If you want to update dependencies that reside within this base image, you can trigger a new image build.
One quick way to accomplish this is by opening a pull request with an empty commit.
```
git commit --allow-empty -m "Triggering image build"
```
Once the PR with the empty commit is merged, it will pull in the latest version of the ubi8/ubi-minimal image during build. Afterwards, a new image tag with the updated dependencies will be available in Quay.

### Updating direct dependencies

At the present moment, the direct dependencies are listed in three places:

* `pyproject.toml`
* `setup.py`
* `requirements.txt` (This does not get used by storage broker, it was added to accomodate a security scanner)

To update a direct dependency, find out where the dependency is listed and bump it up to the desired version.
Then, run `poetry update` to update `poetry.lock`.
This poetry update command will look into the `pyproject.toml` file and "lock" your changes in place.

Once the `poetry update` command is successful, it is recommended to do a simple manual test (Follow Step 1-3 under the "Local Development" section).
Finally, you can open a PR and merge it to finish updating the direct dependencies.

## Authors

Stephen Adams - Initial Work - [SteveHNH](https://www.github.com/SteveHNH)
Dalia Cervantes - Update
