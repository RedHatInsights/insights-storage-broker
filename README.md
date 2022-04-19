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


## Support for Notifications

Storage Broker can interact with the notifications service in order to send our reports of failed payloads to customers. In order to take advantage of the service, the validator must send some additional keys so that the proper message can be assembled to the end user.

    {
        "request_id": <request_id>,
        "account": "123456",
        "reason": "the payload failed because <error>"
        "hostname": "bigserver1",
        "system_id": <system_id>,
        "reporter": <system rejecting the payload>
    }


## Normalizers

In order to make Storage Broker more dynamic, it supports the ability for a user to define their own data normalizer to provide the required keys to the service. Normalizers can be found in `normalizers.py` and more can be added
if need be, or a service can choose to use an existing normalizer.

The only requirmeent for Storage Broker to determine which normalizer to use is that the `service` key is available in the root of the JSON being parsed. This is provided by ingress messages by default. Any other keys to be used must be
added as attributes of your normalizer class.

The only **required** keys in a normalizer at this point are `size`, `service`, and `request_id`. Any other keys you establish can be used for formatting the resulting object filename.

## Available Message

Available Message:

      {
          "account": <account number>,
          "request_id": <uuid for the payload>,
          "principal": <currently the org ID>,
          "service": <the service that validated the payload>,
          "category": <a category for the payload>,
          "url": <URL to download the file>,
          "b64_identity": <the base64 encoded identity of the sender>,
          "id": <host based inventory id if available>, **RELOCATING TO EXTRAS**
          "satellite_managed": <boolean if the system is managed by satellite>, **RELOCATING TO EXTRAS**
          "timestamp": <the time the available message was put on the topic>,
          "validation": <success|failure>,
          "size": <size in bytes of payload>,
          "metadata": <metadata attached to the original upload>,
          "extras": {
              "satellite_managed": <same as above>
              "id": <same as above>
              ...
          }
      }

## Local Development

### Prerequisites

* Python 3.6
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

## Authors

Stephen Adams - Initial Work - [SteveHNH](https://www.github.com/SteveHNH)
