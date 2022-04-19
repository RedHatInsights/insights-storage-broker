from prometheus_client import Histogram, Counter, Summary

# Counters
message_consume_error_count = Counter(
    "storage_broker_message_consume_error_count", "Total consumption errors in consumer"
)
message_consume_count = Counter(
    "storage_broker_message_consume_count", "Total count of consumed messages"
)
message_publish_count = Counter(
    "storage_broker_message_publish_count", "Total messages published on kafka"
)
message_publish_error = Counter(
    "storage_broker_message_publish_error_count",
    "Total messages that failed to publish",
)
message_json_unpack_error = Counter(
    "storage_broker_message_json_upack_error_count",
    "Total message with bad json",
    ["topic"],
)
storage_copy_error = Counter(
    "storage_broker_object_copy_error_count",
    "Total errors encountered by the copy operation",
    ["bucket"],
)
storage_copy_success = Counter(
    "storage_broker_object_copy_success_count",
    "Total successful object moves",
    ["bucket"],
)
invalid_validation_status = Counter(
    "storage_broker_invalid_status_count",
    "Total invalid status messages received",
    ["service"],
)

# Summaries
payload_size = Summary(
    "storage_broker_payload_size_bytes",
    "Total size in bytes of payload to store",
    ["service"],
)

# Histograms
get_key_time = Histogram(
    "storage_broker_get_key_function_time_seconds",
    "Total time to get the key and bucket destination for payload",
)
storage_copy_time = Histogram(
    "storage_broker_object_copy_time_seconds",
    "Total time it takes to copy an object from one bucket to another",
)
presigned_url_gen_time = Histogram(
    "storage_broker_presigned_url_gen_time_seconds",
    "Total time it takes to generate a presigned url for a payload",
)
