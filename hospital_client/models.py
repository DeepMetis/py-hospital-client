from enum import Enum
from typing import Annotated, Union
from pydantic import (
    BaseModel,
    Field,
    field_serializer,
    field_validator,
    model_serializer,
)


class IntervalUnit(str, Enum):
    MINUTES = "minutes"
    HOURS = "hours"


class Interval(BaseModel):
    unit: IntervalUnit
    value: float


class PluginType(str, Enum):
    CHECKER_ACTIVE = "active"
    CHECKER_PULSE = "pulse"
    HANDLER_LOG = "log"
    HANDLER_SLACK = "slack"


class CheckerActiveWrapper(BaseModel):
    type: PluginType = Field(PluginType.CHECKER_ACTIVE, exclude=True)
    url: str
    expected_status: int = 200


class CheckerPulseWrapper(Interval, BaseModel):
    type: PluginType = Field(PluginType.CHECKER_PULSE, exclude=True)


class HandlerLogWrapper(BaseModel):
    type: PluginType = Field(PluginType.HANDLER_LOG, exclude=True)


class HandlerSlackWrapper(BaseModel):
    type: PluginType = Field(PluginType.HANDLER_SLACK, exclude=True)
    hook_url: str


CheckWrappers = Annotated[
    Union[CheckerActiveWrapper, CheckerPulseWrapper], Field(discriminator="type")
]
HandlerWrappers = Annotated[
    Union[HandlerLogWrapper, HandlerSlackWrapper], Field(discriminator="type")
]


class WrapperAnon(BaseModel):
    type: PluginType
    data: dict

    @model_serializer
    def ser_model(self) -> dict:
        return self.data


def check_wrapper(anon_plugin: WrapperAnon) -> CheckWrappers:
    match anon_plugin.type:
        case PluginType.CHECKER_ACTIVE:
            return CheckerActiveWrapper(
                type=PluginType.CHECKER_ACTIVE, **anon_plugin.model_dump()
            )
        case PluginType.CHECKER_PULSE:
            return CheckerPulseWrapper(
                type=PluginType.CHECKER_PULSE, **anon_plugin.model_dump()
            )
        case _:
            raise ValueError(f"Unsupported checker type: {anon_plugin.type}")


def failure_handler_wrapper(anon_plugin: WrapperAnon) -> HandlerWrappers:
    match anon_plugin.type:
        case PluginType.HANDLER_LOG:
            return HandlerLogWrapper(
                type=PluginType.HANDLER_LOG, **anon_plugin.model_dump()
            )
        case PluginType.HANDLER_SLACK:
            return HandlerSlackWrapper(
                type=PluginType.HANDLER_SLACK, **anon_plugin.model_dump()
            )
        case _:
            raise ValueError(f"Unsupported failure handler type: {anon_plugin.type}")


class Service(BaseModel):
    base_url: str = Field(..., exclude=True)
    key: str
    password: str
    handlers_interval: Interval
    check_plugins: list[CheckWrappers]
    failure_handlers: list[HandlerWrappers]

    @field_validator("check_plugins", mode="before")
    def validate_check_plugins(cls, v: list[WrapperAnon]) -> list[CheckWrappers]:
        return [check_wrapper(plugin) for plugin in v]

    @field_serializer("check_plugins")
    def transform_check_plugins(self, v: list[CheckWrappers]) -> list[WrapperAnon]:
        return [WrapperAnon(type=plugin.type, data=plugin.model_dump()) for plugin in v]

    @field_validator("failure_handlers", mode="before")
    def validate_failure_handlers(cls, v: list[WrapperAnon]) -> list[HandlerWrappers]:
        return [failure_handler_wrapper(plugin) for plugin in v]

    @field_serializer("failure_handlers")
    def transform_failure_handlers(self, v: list[HandlerWrappers]) -> list[WrapperAnon]:
        return [WrapperAnon(type=plugin.type, data=plugin.model_dump()) for plugin in v]
