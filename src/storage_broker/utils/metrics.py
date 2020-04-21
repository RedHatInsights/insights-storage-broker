from prometheus_client import Histogram, Counter

# Counters
message_consume_error_count = Counter("storage_broker_message_consume_error_count", "Total consumption errors in consumer")
message_consume_count = Counter("storage_broker_message_consume_count", "Total count of consumed messages")
message_publish_count = Counter("storage_broker_message_publish_count", "Total messages published on kafka")
message_publish_error = Counter("storage_broker_message_publish_error_count", "Total messages that failed to publish")
message_json_unpack_error = Counter("storage_broker_message_json_upack_error_count", "Total message with bad json")
storage_copy_error = Counter("storage_broker_object_copy_error_count", "Total errors encountered by the copy operation")
storage_copy_success = Counter("storage_broker_object_copy_success_count", "Total successful object moves")
storage_put_error = Counter("storage_broker_object_put_error_count", "Total errors for upload operations")
storage_put_success = Counter("storage_broker_object_put_success_count", "Total successful upload operations")
invalid_validation_status = Counter("storage_broker_invalid_status_count", "Total invalid status messages received")


# Summaries
get_key_time = Histogram("storage_broker_get_key_function_time_seconds", "Total time to get the key and bucket destination for payload")
storage_copy_time = Histogram("storage_broker_object_copy_time_seconds", "Total time it takes to copy an object from one bucket to another")
