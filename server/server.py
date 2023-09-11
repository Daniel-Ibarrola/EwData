""" Server that received data from earthworm and forwards it to another client
"""
import os
from socketlib import ServerReceiver, ServerSender, WatchDog, get_module_logger


def main():
    logger = get_module_logger("EWServer", "dev", use_file_handler=False)

    receive_address = (
        os.environ.get("RECEIVE_IP", "localhost"),
        int(os.environ.get("RECEIVE_PORT", 13380))
    )
    send_address = (
        os.environ.get("SEND_IP", "localhost"),
        int(os.environ.get("SEND_PORT", 13381))
    )
    logger.info(f"Receive address is {receive_address}")
    logger.info(f"Send address is {send_address}")

    receiver = ServerReceiver(
        address=receive_address,
        reconnect=False,
        timeout=5,
        logger=logger
    )
    sender = ServerSender(
        address=send_address,
        to_send=receiver.received,
        reconnect=True,
        timeout=2,
        logger=logger
    )
    watchdog = WatchDog(
        {"receive": receiver.receive_thread, "send": sender.send_thread},
        logger=logger
    )

    with receiver:
        with sender:

            receiver.start()
            sender.start()
            watchdog.start()

            try:
                watchdog.join()
            except KeyboardInterrupt:
                watchdog.shutdown()
            finally:
                receiver.shutdown()
                sender.shutdown()

    logger.info(f"Graceful shutdown")


if __name__ == "__main__":
    main()
