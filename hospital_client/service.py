from Crypto.PublicKey import RSA
import aiohttp

from hospital_client.models import Service
from hospital_client.http_signatures import add_signature_headers


class HospitalizedService:
    async def __init__(self, service: Service, rsa_key: RSA.RsaKey):
        self.service = service
        self.rsa_key = rsa_key

    async def pulse(self):
        service = self.service
        async with aiohttp.ClientSession() as session:
            url = f"{service.base_url}/service/pulse"
            session_with_headers = add_signature_headers(
                session, f"{service.key}:{service.password}", self.rsa_key
            )
            if session_with_headers is None:
                return False

            async with session.put(
                url, json={"key": service.key, "pass": service.password}
            ) as response:
                return response.status == 200

    async def update(self):
        service = self.service
        async with aiohttp.ClientSession() as session:
            url = f"{service.base_url}/service/update"
            session_with_headers = add_signature_headers(
                session, f"{service.key}:{service.password}", self.rsa_key
            )
            if session_with_headers is None:
                return False

            async with session.put(url, json=service.model_dump()) as response:
                return response.status == 200

    async def unregister(self):
        service = self.service
        async with aiohttp.ClientSession() as session:
            url = f"{service.base_url}/service/unregister"
            session_with_headers = add_signature_headers(
                session, f"{service.key}:{service.password}", self.rsa_key
            )
            if session_with_headers is None:
                return False

            async with session.delete(
                url, json={"key": service.key, "pass": service.password}
            ) as response:
                return response.status == 200
