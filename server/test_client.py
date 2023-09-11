""" Client to test earthworm server
"""
import os
import queue
from socketlib import AbstractService, ClientSender, WatchDog, get_module_logger
import time


class MessageGenerator(AbstractService):

    @property
    def messages(self) -> queue.Queue[str]:
        return self._out

    def _handle_message(self):
        while not self._stop():
            msgs = [
                "S160,HL1,19644550,3,100,200,300",
                "S160,HL2,19644550,3,100,200,300",
                "S160,HLZ,19644550,3,100,200,300"
            ]
            for msg in msgs:
                self.messages.put(msg)
            time.sleep(1)


def main():
    logger = get_module_logger("TestClient", "dev", use_file_handler=False)
    address = (
        os.environ.get("RECEIVE_IP", "localhost"),
        int(os.environ.get("RECEIVE_PORT", 13380))
    )
    logger.info(f"Client will connect to {address}")

    msg_gen = MessageGenerator(logger=logger)
    client = ClientSender(
        address=address,
        to_send=msg_gen.messages,
        reconnect=False,
        timeout=5,
        logger=logger
    )
    watchdog = WatchDog(
        {"send": client.send_thread, "generator": msg_gen.process_thread},
        logger
    )

    with client:
        client.connect()
        client.start()
        msg_gen.start()
        watchdog.start()

        try:
            watchdog.join()
        except KeyboardInterrupt:
            watchdog.shutdown()
        finally:
            msg_gen.shutdown()
            client.shutdown()

    logger.info("Graceful shutdown")


if __name__ == "__main__":
    main()
