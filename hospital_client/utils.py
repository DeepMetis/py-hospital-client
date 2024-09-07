import logging

from typing import Callable
from pydantic.alias_generators import to_camel


logger = logging.getLogger("hospital-client")


def transform_dict_keys(
    d: dict, key_converter: Callable[[str], str] = to_camel
) -> dict:
    def convert(item):
        if isinstance(item, dict):
            return transform_dict_keys(item, key_converter)
        elif isinstance(item, list):
            return [convert(i) for i in item]
        return item

    return {key_converter(k): convert(v) for k, v in d.items()}
