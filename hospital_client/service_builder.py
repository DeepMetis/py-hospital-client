import asyncio
import aiohttp

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


from hospital_client.utils import transform_dict_keys, logger
from hospital_client.models import (
    CheckWrappers,
    CheckerActiveWrapper,
    CheckerPulseWrapper,
    HandlerLogWrapper,
    HandlerSlackWrapper,
    HandlerWrappers,
    Interval,
    IntervalUnit,
    PluginType,
    Service,
)
from hospital_client.service import HospitalService, PulseWorker
from hospital_client.http_signatures import load_rsa_key, add_signature_headers


class ServiceBuilder:
    def __init__(
        self,
        base_url: str,
        key: str,
        code: str,
        private_key_path: str = "./certs/private_key.pem",
    ):
        self.base_url = base_url
        self.key = key
        self.code = code
        self.private_key = load_rsa_key(private_key_path)
        self.hospital_service: HospitalService | None = None
        self.handlers_interval = Interval(unit=IntervalUnit.HOURS, value=1)
        self.check_plugins: list[CheckWrappers] = []
        self.failure_handlers: list[HandlerWrappers] = []
        self.has_registered = False

    async def _exists(self) -> HospitalService | None:
        if self.hospital_service is not None:
            return self.hospital_service

        async with aiohttp.ClientSession() as session:
            url = f"{self.base_url}/service"
            session_with_headers = add_signature_headers(
                session, self.key, self.private_key
            )
            if session_with_headers is None:
                return
            async with session.get(
                url, params={"key": self.key, "code": self.code}
            ) as response:
                if response.status != 200:
                    return
                data = await response.json()
                try:
                    service = Service(base_url=self.base_url, **data)
                    self.has_registered = True
                    return HospitalService(service=service, rsa_key=self.private_key)
                except Exception as e:
                    logger.error(e)
                    return

    async def _register(self, service: Service) -> bool:
        if self.hospital_service is not None:
            return True

        async with aiohttp.ClientSession() as session:
            url = f"{self.base_url}/service/register"
            session_with_headers = add_signature_headers(
                session, self.key, self.private_key
            )
            if session_with_headers is None:
                return False

            payload = transform_dict_keys(service.model_dump())
            async with session.post(url, json=payload) as response:
                return response.status == 201

    async def build(self) -> HospitalService | None:
        if self.hospital_service is not None and self.has_registered:
            return self.hospital_service

        if len(self.check_plugins) == 0 or len(self.failure_handlers) == 0:
            return

        self.hospital_service = await self._exists()
        if self.hospital_service is not None:
            self.has_registered = True
            self.hospital_service.service.handlers_interval = self.handlers_interval
            self.hospital_service.service.check_plugins = self.check_plugins
            self.hospital_service.service.failure_handlers = self.failure_handlers
            await self.hospital_service.update()
            return self.hospital_service

        service = Service(
            base_url=self.base_url,
            key=self.key,
            code=self.code,
            handlers_interval=self.handlers_interval,
            check_plugins=self.check_plugins,
            failure_handlers=self.failure_handlers,
        )
        if await self._register(service):
            self.hospital_service = HospitalService(
                service=service, rsa_key=self.private_key
            )
            self.has_registered = True
            return self.hospital_service

    def interval(self, interval: Interval):
        self.handlers_interval = interval
        return self

    def add_checks(self, data: CheckWrappers | list[CheckWrappers]):
        if isinstance(data, list):
            self.check_plugins.extend(data)
            return self

        self.check_plugins.append(data)
        return self

    def add_failure_handlers(self, data: HandlerWrappers | list[HandlerWrappers]):
        if isinstance(data, list):
            self.failure_handlers.extend(data)
            return self

        self.failure_handlers.append(data)
        return self


async def test():
    builder = ServiceBuilder("http://localhost:8080", "test", "test")
    builder = builder.interval(Interval(unit=IntervalUnit.MINUTES, value=10))
    builder = builder.add_checks(
        [
            CheckerActiveWrapper(
                type=PluginType.CHECKER_ACTIVE,
                url="https://wealthy-entirely-cow.ngrok-free.app/ping",
            ),
            CheckerPulseWrapper(
                type=PluginType.CHECKER_PULSE, unit=IntervalUnit.SECONDS, value=30
            ),
        ]
    )
    builder = builder.add_failure_handlers(
        [
            HandlerLogWrapper(type=PluginType.HANDLER_LOG),
            HandlerSlackWrapper(
                type=PluginType.HANDLER_SLACK,
                hook_url="https://hooks.slack.com/triggers/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",
            ),
        ]
    )

    hospital_service = await builder.build()
    if hospital_service is None:
        logger.error("Failed to build hospital service")
        return
    pulse_worker = PulseWorker(hospital_service.pulse, pulse_interval=5)
    await pulse_worker.work()
    try:
        while True:
            await asyncio.sleep(1)
    except Exception:
        logger.error(
            "Stopping the worker",
        )
        pulse_worker.cancel()
    finally:
        ok = await hospital_service.unregister()
        logger.info("Unregistered service:", ok)


if __name__ == "__main__":
    asyncio.run(test())
