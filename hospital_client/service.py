from abc import ABC, abstractmethod
import asyncio
from typing import Any, Callable, Coroutine
from Crypto.PublicKey import RSA
import aiohttp

from utils import transform_dict_keys, logger
from models import Service
from http_signatures import add_signature_headers


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
                else:
                    tries = 3
                if tries <= 0:
                    self.cancel()
                    break
                await asyncio.sleep(self.pulse_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(e)
                continue

    def update_interval(self, pulse_interval: int):
        self.pulse_interval = max(pulse_interval, 1)


class HospitalService:
    def __init__(self, service: Service, rsa_key: RSA.RsaKey):
        self.service = service
        self.rsa_key = rsa_key

    async def pulse(self):
        service = self.service
        async with aiohttp.ClientSession() as session:
            url = f"{service.base_url}/service/pulse"
            session_with_headers = add_signature_headers(
                session, service.key, self.rsa_key
            )
            if session_with_headers is None:
                return False

            async with session.put(
                url, json={"key": service.key, "code": service.code}
            ) as response:
                return response.status == 200

    async def update(self):
        service = self.service
        async with aiohttp.ClientSession() as session:
            url = f"{service.base_url}/service/update"
            session_with_headers = add_signature_headers(
                session, service.key, self.rsa_key
            )
            if session_with_headers is None:
                return False
            data = transform_dict_keys(service.model_dump())
            async with session.put(url, json=data) as response:
                return response.status == 200

    async def unregister(self):
        service = self.service
        async with aiohttp.ClientSession() as session:
            url = f"{service.base_url}/service/unregister"
            session_with_headers = add_signature_headers(
                session, service.key, self.rsa_key
            )
            if session_with_headers is None:
                return False

            async with session.delete(
                url, json={"key": service.key, "code": service.code}
            ) as response:
                return response.status == 200
