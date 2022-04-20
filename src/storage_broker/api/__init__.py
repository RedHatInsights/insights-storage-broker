from socket import timeout
from time import time
import uuid
from datetime import datetime, timezone, timedelta
from flask import Flask, request, jsonify

from src.storage_broker.storage import aws
from src.storage_broker.utils import broker_logging, config


app = Flask(__name__)
logger = broker_logging.initialize_logging()


@app.route("/archive/url/", methods=['GET'])
def get_archive_url():    
    request_id = request.args.get("request_id")
    if not request_id:
        return error_message('request_id param missing'), 400

    try:
        uuid.UUID(request_id)
    except ValueError:
        return error_message('invalid request_id'), 400

    key_check_exception = aws.check_key(config.STAGE_BUCKET, request_id)
    if key_check_exception:
        client_error_msg, error_code = key_check_exception.response["Error"]["Message"], key_check_exception.response["Error"]["Code"]
        return error_message(f"{client_error_msg} - {error_code}"), 400

    url = aws.get_url(config.STAGE_BUCKET, request_id, config.API_URL_EXPIRY)

    timeout = datetime.utcnow() + timedelta(seconds=config.API_URL_EXPIRY)
    timeout_str = str(timeout.replace(microsecond=0, tzinfo=timezone.utc).isoformat())

    response = {"request_id": request_id, "url": url, "timeout": timeout_str}

    return jsonify(response)


def main():
    logger.info("Starting storage broker api...")
    app.run(port=config.API_PORT)


def error_message(message):
    return jsonify({"message": message})


if __name__ == "__main__":
    main()
