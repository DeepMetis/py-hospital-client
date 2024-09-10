import aiohttp

from Crypto.PublicKey import RSA

from hospital_client.utils import transform_dict_keys
from hospital_client.models import Service
from hospital_client.http_signatures import add_signature_headers


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
            url = f"{service.base_url}/service"
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
