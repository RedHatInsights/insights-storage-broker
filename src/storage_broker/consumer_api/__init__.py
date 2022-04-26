import imp
from logging import shutdown
import signal
from concurrent.futures import ThreadPoolExecutor, thread

from src.storage_broker.app import main as consumer
from src.storage_broker.api import main as api

shutdown = False

def handle_shutdown(signal, frame):
    global shutdown
    shutdown = True

signal.signal(signal.SIGTERM, handle_shutdown)

def main():
    with ThreadPoolExecutor(max_workers=2) as executor:
        executor.submit(consumer)
        executor.submit(api)

        while True:
            if shutdown:
                executor._threads.clear()
                thread._threads_queues.clear()
                break


if __name__ == "__main__":
    main()
