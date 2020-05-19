import datetime


def get_time():
    return datetime.datetime.now().isoformat()


def create_msg(data, status, status_msg):
    msg = {
        "service": "insights-storage-broker",
        "account": data.get("account"),
        "request_id": data.get("request_id"),
        "inventory_id": data.get("id"),
        "status": status,
        "status_msg": status_msg,
        "date": get_time(),
    }

    return msg
