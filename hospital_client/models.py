from enum import Enum
from typing import Literal
from typing import Annotated, Union
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_serializer,
    field_validator,
)
from pydantic.alias_generators import to_camel


class CamelCaseBaseModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class IntervalUnit(str, Enum):
    SECONDS = "seconds"
    MINUTES = "minutes"
    HOURS = "hours"


class Interval(CamelCaseBaseModel):
    unit: IntervalUnit
    value: float


class PluginType(str, Enum):
    CHECKER_ACTIVE = "active"
    CHECKER_PULSE = "pulse"
    HANDLER_LOG = "log"
    HANDLER_SLACK = "slack"


class CheckerActiveWrapper(CamelCaseBaseModel):
    type: Literal[PluginType.CHECKER_ACTIVE] = Field(
        Literal[PluginType.CHECKER_ACTIVE], exclude=True
    )
    url: str
    expected_status: int = 200


class CheckerPulseWrapper(Interval, CamelCaseBaseModel):
    type: Literal[PluginType.CHECKER_PULSE] = Field(
        Literal[PluginType.CHECKER_PULSE], exclude=True
    )


class HandlerLogWrapper(CamelCaseBaseModel):
    type: Literal[PluginType.HANDLER_LOG] = Field(
        Literal[PluginType.HANDLER_LOG], exclude=True
    )


class HandlerSlackWrapper(CamelCaseBaseModel):
    type: Literal[PluginType.HANDLER_SLACK] = Field(
        PluginType.HANDLER_SLACK, exclude=True
    )
    hook_url: str


CheckWrappers = Annotated[
    Union[CheckerActiveWrapper, CheckerPulseWrapper], Field(discriminator="type")
]
HandlerWrappers = Annotated[
    Union[HandlerLogWrapper, HandlerSlackWrapper], Field(discriminator="type")
]


class WrapperAnon(CamelCaseBaseModel):
    type: PluginType
    data: dict


def check_wrapper(anon_plugin: WrapperAnon) -> CheckWrappers:
    match anon_plugin.type:
        case PluginType.CHECKER_ACTIVE:
            return CheckerActiveWrapper(
                type=PluginType.CHECKER_ACTIVE, **anon_plugin.data
            )
        case PluginType.CHECKER_PULSE:
            return CheckerPulseWrapper(
                type=PluginType.CHECKER_PULSE, **anon_plugin.data
            )
        case _:
            raise ValueError(f"Unsupported checker type: {anon_plugin.type}")


def failure_handler_wrapper(anon_plugin: WrapperAnon) -> HandlerWrappers:
    match anon_plugin.type:
        case PluginType.HANDLER_LOG:
            return HandlerLogWrapper(type=PluginType.HANDLER_LOG, **anon_plugin.data)
        case PluginType.HANDLER_SLACK:
            return HandlerSlackWrapper(
                type=PluginType.HANDLER_SLACK, **anon_plugin.data
            )
        case _:
            raise ValueError(f"Unsupported failure handler type: {anon_plugin.type}")


class Service(CamelCaseBaseModel):
    base_url: str = Field(..., exclude=True)
    key: str
    code: str
    handlers_interval: Interval
    check_plugins: list[CheckWrappers]
    failure_handlers: list[HandlerWrappers]

    @field_validator("check_plugins", mode="before")
    def validate_check_plugins(cls, v: list[dict]) -> list[CheckWrappers]:
        plugins: list[CheckWrappers] = []
        for i in range(len(v)):
            plugin = v[i]
            try:
                plugin = WrapperAnon(**v[i])
            except Exception as e:
                raise ValueError(e)
            plugin = check_wrapper(plugin)
            plugins.append(plugin)
        return plugins

    @field_serializer("check_plugins")
    def transform_check_plugins(self, v: list[CheckWrappers]) -> list[WrapperAnon]:
        return [WrapperAnon(type=plugin.type, data=plugin.model_dump()) for plugin in v]

    @field_validator("failure_handlers", mode="before")
    def validate_failure_handlers(cls, v: list[dict]) -> list[HandlerWrappers]:
        plugins: list[HandlerWrappers] = []
        for i in range(len(v)):
            plugin = v[i]
            try:
                plugin = WrapperAnon(**v[i])
            except Exception as e:
                raise ValueError(e)
            plugin = failure_handler_wrapper(plugin)
            plugins.append(plugin)
        return plugins

    @field_serializer("failure_handlers")
    def transform_failure_handlers(self, v: list[HandlerWrappers]) -> list[WrapperAnon]:
        return [WrapperAnon(type=plugin.type, data=plugin.model_dump()) for plugin in v]
