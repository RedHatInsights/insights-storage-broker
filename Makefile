produce_validation_message:
	BOOTSTRAP_SERVERS=localhost:29092 BUCKET_MAP_FILE=default_map.yaml python utils/produce_message.py
