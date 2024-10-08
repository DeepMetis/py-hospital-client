import asyncio

from abc import ABC, abstractmethod
from typing import Any, Callable, Coroutine

from hospital_client.utils import logger


class HospitalWorker(ABC):
    @abstractmethod
    def start(self):
        pass

    @abstractmethod
    def cancel(self):
        pass

    @abstractmethod
    def restart():
        pass

    @abstractmethod
    async def work(self):
        pass


class PulseWorker(HospitalWorker):
    def __init__(self, cb: Callable[[], Coroutine[Any, Any, bool]], pulse_interval=10):
        self.cb = cb
        self.pulse_task = None
        self.pulse_interval = max(pulse_interval, 1)

    def start(self):
        if self.pulse_task is not None:
            return
        self.pulse_task = asyncio.create_task(self.work())
        logger.info("started pulse worker")

    def cancel(self):
        if self.pulse_task is None:
            return
        self.pulse_task.cancel()
        self.pulse_task = None
        logger.info("cancelled pulse worker")

    def restart(self):
        self.cancel()
        asyncio.create_task(self.work())
        logger.info("restarted pulse worker")

    async def work(self):
        tries = 3
        while True:
            try:
                ok = await self.cb()
                if not ok:
                    tries -= 1
                    await asyncio.sleep(1)
                    continue

                if ok or tries <= 0:
                    tries = 3
                    await asyncio.sleep(self.pulse_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(e)
                continue

    def update_interval(self, pulse_interval: int):
        self.pulse_interval = max(pulse_interval, 1)
