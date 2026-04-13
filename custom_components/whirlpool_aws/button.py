"""Button platform for Whirlpool Appliances (AWS IoT) — microwave buttons."""

from __future__ import annotations

from typing import override

from whirlpool.microwave import Microwave

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import WhirlpoolConfigEntry
from .entity import WhirlpoolEntity

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: WhirlpoolConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the button platform."""
    appliances_manager = config_entry.runtime_data

    async_add_entities(
        MicrowaveCancelCookButton(mwo)
        for mwo in appliances_manager.microwaves
    )


class MicrowaveCancelCookButton(WhirlpoolEntity, ButtonEntity):
    """Button to cancel the current microwave cook cycle."""

    _appliance: Microwave
    _attr_translation_key = "microwave_cancel_cook"

    def __init__(self, appliance: Microwave) -> None:
        """Initialize the button."""
        super().__init__(appliance, unique_id_suffix="-mwo_cancel_cook")

    @override
    async def async_press(self) -> None:
        """Cancel the cook cycle."""
        MicrowaveCancelCookButton._check_service_request(
            await self._appliance.cancel_cook()
        )
