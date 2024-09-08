import asyncio

from abc import ABC, abstractmethod
from typing import Any, Callable, Coroutine

from hospital_client.utils import logger


class HospitalWorker(ABC):
    @abstractmethod
    async def work(self, cb: Coroutine[Any, Any, Any], interval: int):
        pass

    @abstractmethod
    def cancel(self):
        pass

    @abstractmethod
    def restart():
        pass


class PulseWorker(HospitalWorker):
    def __init__(self, cb: Callable[[], Coroutine[Any, Any, bool]], pulse_interval=10):
        self.cb = cb
        self.pulse_task = None
        self.pulse_interval = max(pulse_interval, 1)

    async def work(self):
        if self.pulse_task:
            self.cancel()
        self.pulse_task = asyncio.create_task(self._pulse())
        logger.info("started pulse worker")

    def cancel(self):
        if self.pulse_task is None:
            return
        self.pulse_task.cancel()
        self.pulse_task = None
        logger.info("cancelled pulse worker")

    def restart(self):
        self.cancel()
        asyncio.create_task(self._pulse())
        logger.info("restarted pulse worker")

    async def _pulse(self):
        tries = 3
        while True:
            try:
                ok = await self.cb()
                if not ok:
                    tries -= 1
                    raise RuntimeError("Pulse check failed")

                if ok or tries <= 0:
                    tries = 3
                    await asyncio.sleep(self.pulse_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(e)
                await asyncio.sleep(2)
                continue

    def update_interval(self, pulse_interval: int):
        self.pulse_interval = max(pulse_interval, 1)
