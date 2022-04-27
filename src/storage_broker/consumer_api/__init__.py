from threading import Event
import signal
from concurrent.futures import ThreadPoolExecutor

from src.storage_broker.app import main as consumer
from src.storage_broker.api import main as api

event = Event()

def signal_handler(signal, frame):
    event.set()

signal.signal(signal.SIGTERM, signal_handler)

def main():
    with ThreadPoolExecutor(max_workers=2) as executor:
        executor.submit(consumer, event)
        executor.submit(api)
        signal.pause()


if __name__ == "__main__":
    main()
