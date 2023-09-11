""" Client that connects to earthworm server to receive seismic data
"""
import logging
import os
import queue

from socketlib import AbstractService, ClientReceiver, get_module_logger, WatchDog
from socketlib.basic.queues import get_from_queue


class WaveLogger(AbstractService):

    def __init__(
            self,
            messages: queue.Queue[bytes],
            logger: logging.Logger
    ):
        super().__init__(in_queue=messages, logger=logger)

    @property
    def messages(self) -> queue.Queue[bytes]:
        return self._in

    def _handle_message(self):
        while not self._stop():
            msg: bytes | None = get_from_queue(self.messages, 2)
            if msg is not None:
                self._logger.info(msg.decode().strip())


def main():
    logger = get_module_logger("EWClient", "dev", use_file_handler=False)
    address = (
        os.environ.get("HOST_IP", "localhost"),
        int(os.environ.get("HOST_PORT", 13381))
    )
    logger.info(f"Client will connect to {address}")

    client = ClientReceiver(
        address=address,
        reconnect=False,
        timeout=5,
        logger=logger
    )
    wave_logger = WaveLogger(client.received, logger)

    threads = {
        "receive": client.receive_thread,
        "waves": wave_logger.process_thread
    }
    watchdog = WatchDog(threads, logger)

    with client:
        client.connect()
        client.start()
        wave_logger.start()
        watchdog.start()

        try:
            watchdog.join()
        except KeyboardInterrupt:
            watchdog.shutdown()
        finally:
            client.shutdown()
            wave_logger.shutdown()

    logger.info("Graceful shutdown")


if __name__ == "__main__":
    main()
