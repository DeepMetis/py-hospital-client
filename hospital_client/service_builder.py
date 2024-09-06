import aiohttp

from hospital_client.models import (
    CheckWrappers,
    HandlerWrappers,
    Interval,
    IntervalUnit,
    Service,
)
from http_signatures import load_rsa_key, add_signature_headers


class ServiceBuilder:
    async def __init__(
        self, base_url: str, key: str, password: str, private_key_path: str
    ):
        self.base_url = base_url
        self.key = key
        self.password = password
        self.private_key = load_rsa_key(private_key_path)
        self.service = await self._exists()
        self.handlers_interval = Interval(unit=IntervalUnit.HOURS, value=1)
        self.check_plugins: list[CheckWrappers] = []
        self.failure_handler_plugins: list[HandlerWrappers] = []
        self.has_registered = False

    async def _exists(self) -> Service | None:
        async with aiohttp.ClientSession() as session:
            url = f"{self.base_url}/service"
            session_with_headers = add_signature_headers(
                session, f"{self.key}:{self.password}", self.private_key
            )
            if session_with_headers is None:
                return

            async with session.get(
                url, params={"key": self.key, "pass": self.password}
            ) as response:
                if response.status != 200:
                    return
                data = await response.json()
                try:
                    service = Service(**data)
                    self.has_registered = True
                    return service
                except Exception as e:
                    print(f"Failed to parse service data: {e}")
                    return

    async def _register(self) -> bool:
        if self.service is None:
            return False

        async with aiohttp.ClientSession() as session:
            url = f"{self.base_url}/service"
            session_with_headers = add_signature_headers(
                session, f"{self.key}:{self.password}", self.private_key
            )
            if session_with_headers is None:
                return False

            async with session.post(url, json=self.service) as response:
                if response.status != 201:
                    return False
                self.has_registered = True
                return True

    async def build(self) -> Service | None:
        if self.service is not None and self.has_registered:
            return self.service

        if len(self.check_plugins) == 0 or len(self.failure_handler_plugins) == 0:
            return

        self.service = Service(
            base_url=self.base_url,
            key=self.key,
            password=self.password,
            handlers_interval=self.handlers_interval,
            check_plugins=self.check_plugins,
            failure_handlers=self.failure_handler_plugins,
        )
        if await self._register():
            return self.service

    def interval(self, interval: Interval):
        self.handlers_interval = interval
        return self

    def add_check(self, data: CheckWrappers):
        self.check_plugins.append(data)
        return self

    def add_failure_handler(self, data: HandlerWrappers):
        self.failure_handler_plugins.append(data)
        return self
