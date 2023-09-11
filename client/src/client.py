""" Client that connects to earthworm server to receive seismic data
"""
import logging
import numpy as np
import os
import queue
from socketlib import AbstractService, ClientReceiver, get_module_logger, WatchDog
from socketlib.basic.queues import get_from_queue
import sys

from data import STATIONS, COUNT_TO_GALS


class WaveAnalyzer(AbstractService):

    def __init__(
            self,
            messages: queue.Queue[bytes],
            station: str,
            channel: str,
            logger: logging.Logger
    ):
        super().__init__(in_queue=messages, logger=logger)
        self.station = station
        self.channel = channel
        self.conv_factor = COUNT_TO_GALS[station]
        self.base_line = 0
        self.means = []

    @property
    def messages(self) -> queue.Queue[bytes]:
        """ A queue of bytes where each element represents a wave from earthworm.

            Messages gave the following format:

                station,channel,time,nSamples,data[0],data[1],...,data[nSamples-1],data[nSamples]

            Example:
                S160,HLZ,19644550,3,100,200,300
        """
        return self._in

    def _handle_message(self):
        while not self._stop():
            msg: bytes | None = get_from_queue(self.messages, 2)
            if msg is not None:
                msg_str = msg.decode()
                if msg_str.startswith(self.station) and msg_str[5:8] == self.channel:
                    data = self.wave_data(msg_str)
                    data = data * self.conv_factor

                    mean = np.mean(data)
                    normalized = data - mean
                    baselined = data - self.base_line

                    self.means.append(mean)
                    if len(self.means) == 30:
                        self.base_line = sum(self.means) / len(self.means)
                        self.means.clear()

                    self.log_data(data, normalized, baselined)

    @staticmethod
    def wave_data(wave: str) -> np.ndarray:
        pieces = wave.split(",")
        n_samples = int(pieces[3])
        data = np.zeros(n_samples, dtype=np.dtype("i4"))
        for ii in range(0, len(pieces) - 4):
            data[ii] = int(pieces[ii + 4])
        return data

    def log_data(
            self,
            original: np.ndarray,
            normalized: np.ndarray,
            baselined: np.ndarray
    ) -> None:
        min_, max_ = original.min(), original.max()
        if abs(min_) > 3 or abs(max_) > 3:
            self._logger.info("Original: min {min_}; max {max_}")

        min_, max_ = normalized.min(), normalized.max()
        if abs(min_) > 3 or abs(max_) > 3:
            self._logger.info("Normalized: min {min_}; max {max_}")

        min_, max_ = baselined.min(), baselined.max()
        if abs(min_) > 3 or abs(max_) > 3:
            self._logger.info("Baselined: min {min_}; max {max_}")


def main():
    if len(sys.argv) > 1:
        station = sys.argv[1]
        if station not in STATIONS:
            raise ValueError(f"Invalid station {station}")
    else:
        station = "S160"
    channel = list(STATIONS[station])[0]

    logger = get_module_logger("EWClient", "dev", use_file_handler=False)
    address = (
        os.environ.get("HOST_IP", "localhost"),
        int(os.environ.get("HOST_PORT", 13381))
    )
    logger.info(f"Client will connect to {address}")
    logger.info(f"Station {station}. Channel {channel}")

    client = ClientReceiver(
        address=address,
        reconnect=False,
        timeout=5,
        logger=logger
    )
    wave_logger = WaveAnalyzer(client.received, station, channel, logger)

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
