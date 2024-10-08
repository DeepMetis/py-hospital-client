import json
import time
import hashlib
import asyncio
import aiohttp

from binascii import hexlify
from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA
from Crypto.Signature import pkcs1_15

from hospital_client.utils import logger


def load_rsa_key(path: str) -> RSA.RsaKey:
    with open(path, "rb") as key_file:
        return RSA.import_key(key_file.read())


def create_signature_headers(
    content, private_key: RSA.RsaKey
) -> tuple[None, Exception] | tuple[dict[str, str], None]:
    created = int(time.time())
    try:
        message = json.dumps(content, sort_keys=True).encode("utf-8")
    except Exception as e:
        return None, e

    content_hash = hashlib.sha256(message).hexdigest()
    hash_obj = SHA256.new(f"{content_hash},{created}".encode("utf-8"))
    signature = pkcs1_15.new(private_key).sign(hash_obj)
    return {
        "content-type": "application/json",
        "accept": "application/json",
        "content-digest": f"sha256={content_hash}",
        "signature-input": f'sig1=("content-digest");created={created}',
        "signature": f"sig1={hexlify(signature).decode('utf-8')}",
    }, None


def add_signature_headers(
    session: aiohttp.ClientSession, data: str, private_key: RSA.RsaKey
):
    headers, error = create_signature_headers(data, private_key)
    if error is not None or headers is None:
        logger.info("could not add signature headers to session")
        return

    [session.headers.add(header, val) for header, val in headers.items()]
    return session


async def test():
    rsa_key = load_rsa_key("./certs/private_key.pem")
    key = "test"
    code = "test"
    async with aiohttp.ClientSession() as session:
        url = "http://localhost:8080/service"
        payload = {
            "key": key,
            "code": code,
            "handlersInterval": {"unit": "minutes", "value": 1},
            "checkPlugins": [{"type": "pulse", "data": {"max_allowed_interval": 20}}],
            "failureHandlers": [{"type": "log", "data": {}}],
        }
        headers, error = create_signature_headers(
            code,
            rsa_key,
        )
        if error is not None or headers is None:
            return
        [session.headers.add(header, val) for header, val in headers.items()]
        async with session.post(url, json=payload) as response:
            logger.info(response.status)
            logger.info(await response.json())


if __name__ == "__main__":
    asyncio.run(test())
