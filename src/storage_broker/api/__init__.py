import uuid
from flask import Flask, request, jsonify

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

    sample_response = {"request_id": request_id, "url": "https://example.com/", "timeout": "2022-04-14T19:58:51.598Z"}

    return jsonify(sample_response)


def main():
    logger.info("Starting storage broker api...")
    app.run(port=config.API_PORT)


def error_message(message):
    return jsonify({"message": message})


if __name__ == "__main__":
    main()