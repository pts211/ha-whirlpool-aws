"""Switch platform for Whirlpool Appliances (AWS IoT) — microwave switches."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, override

from whirlpool_aws.microwave import Microwave

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import WhirlpoolConfigEntry
from .entity import WhirlpoolEntity

PARALLEL_UPDATES = 1


@dataclass(frozen=True, kw_only=True)
class WhirlpoolSwitchDescription(SwitchEntityDescription):
    """Describes a Whirlpool switch entity."""

    is_on_fn: Callable[[Microwave], bool | None]
    turn_on_fn: Callable[[Microwave], Awaitable[bool]]
    turn_off_fn: Callable[[Microwave], Awaitable[bool]]
    supported_fn: Callable[[Microwave], bool] = lambda _mwo: True


MICROWAVE_SWITCHES: tuple[WhirlpoolSwitchDescription, ...] = (
    WhirlpoolSwitchDescription(
        key="mwo_cavity_light",
        translation_key="microwave_cavity_light",
        is_on_fn=lambda mwo: mwo.get_cavity_light(),
        turn_on_fn=lambda mwo: mwo.set_cavity_light(True),
        turn_off_fn=lambda mwo: mwo.set_cavity_light(False),
    ),
    WhirlpoolSwitchDescription(
        key="mwo_control_lock",
        translation_key="microwave_control_lock",
        is_on_fn=lambda mwo: mwo.get_control_locked(),
        turn_on_fn=lambda mwo: mwo.set_control_locked(True),
        turn_off_fn=lambda mwo: mwo.set_control_locked(False),
        supported_fn=lambda mwo: mwo.supports_control_lock,
    ),
    WhirlpoolSwitchDescription(
        key="mwo_quiet_mode",
        translation_key="microwave_quiet_mode",
        is_on_fn=lambda mwo: mwo.get_quiet_mode(),
        turn_on_fn=lambda mwo: mwo.set_quiet_mode(True),
        turn_off_fn=lambda mwo: mwo.set_quiet_mode(False),
        supported_fn=lambda mwo: mwo.supports_quiet_mode,
    ),
    WhirlpoolSwitchDescription(
        key="mwo_sabbath_mode",
        translation_key="microwave_sabbath_mode",
        is_on_fn=lambda mwo: mwo.get_sabbath_mode(),
        turn_on_fn=lambda mwo: mwo.set_sabbath_mode(True),
        turn_off_fn=lambda mwo: mwo.set_sabbath_mode(False),
        supported_fn=lambda mwo: mwo.supports_sabbath_mode,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: WhirlpoolConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the switch platform."""
    appliances_manager = config_entry.runtime_data

    async_add_entities(
        WhirlpoolSwitch(mwo, description)
        for mwo in appliances_manager.microwaves
        for description in MICROWAVE_SWITCHES
        if description.supported_fn(mwo)
    )


class WhirlpoolSwitch(WhirlpoolEntity, SwitchEntity):
    """Whirlpool microwave switch entity."""

    _appliance: Microwave

    def __init__(
        self, appliance: Microwave, description: WhirlpoolSwitchDescription
    ) -> None:
        """Initialize the switch."""
        super().__init__(appliance, unique_id_suffix=f"-{description.key}")
        self.entity_description: WhirlpoolSwitchDescription = description

    @override
    @property
    def is_on(self) -> bool | None:
        """Return true if the switch is on."""
        return self.entity_description.is_on_fn(self._appliance)

    @override
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        WhirlpoolSwitch._check_service_request(
            await self.entity_description.turn_on_fn(self._appliance)
        )

    @override
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        WhirlpoolSwitch._check_service_request(
            await self.entity_description.turn_off_fn(self._appliance)
        )
