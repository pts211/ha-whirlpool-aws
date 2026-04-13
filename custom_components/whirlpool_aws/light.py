"""Light platform for Whirlpool Appliances (AWS IoT) — microwave hood light."""

from __future__ import annotations

from typing import Any, override

from whirlpool_aws.microwave import HoodLightColor, HoodLightLevel, Microwave

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_EFFECT,
    ColorMode,
    LightEntity,
    LightEntityFeature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import WhirlpoolConfigEntry
from .entity import WhirlpoolEntity

PARALLEL_UPDATES = 1

# Map HoodLightLevel to a 0-255 brightness scale (4 discrete steps).
_LEVEL_TO_BRIGHTNESS: dict[HoodLightLevel, int] = {
    HoodLightLevel.Off: 0,
    HoodLightLevel.Low: 85,
    HoodLightLevel.Medium: 170,
    HoodLightLevel.High: 255,
}

_BRIGHTNESS_TO_LEVEL: list[tuple[int, HoodLightLevel]] = [
    (43, HoodLightLevel.Off),
    (128, HoodLightLevel.Low),
    (213, HoodLightLevel.Medium),
    (255, HoodLightLevel.High),
]

_COLOR_EFFECTS: dict[str, HoodLightColor] = {
    "Warm White": HoodLightColor.WarmWhite,
    "Natural White": HoodLightColor.NaturalWhite,
    "Cool White": HoodLightColor.CoolWhite,
}

_COLOR_TO_EFFECT: dict[HoodLightColor, str] = {v: k for k, v in _COLOR_EFFECTS.items()}


def _brightness_to_level(brightness: int) -> HoodLightLevel:
    """Convert a 0-255 brightness value to the nearest HoodLightLevel."""
    for threshold, level in _BRIGHTNESS_TO_LEVEL:
        if brightness <= threshold:
            return level
    return HoodLightLevel.High


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: WhirlpoolConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the light platform."""
    appliances_manager = config_entry.runtime_data

    async_add_entities(
        MicrowaveHoodLight(mwo)
        for mwo in appliances_manager.microwaves
    )


class MicrowaveHoodLight(WhirlpoolEntity, LightEntity):
    """Hood light with discrete brightness levels and color presets."""

    _appliance: Microwave
    _attr_translation_key = "microwave_hood_light"
    _attr_color_mode = ColorMode.BRIGHTNESS
    _attr_supported_color_modes = {ColorMode.BRIGHTNESS}
    _attr_supported_features = LightEntityFeature.EFFECT
    _attr_effect_list = list(_COLOR_EFFECTS.keys())

    def __init__(self, appliance: Microwave) -> None:
        """Initialize the light."""
        super().__init__(appliance, unique_id_suffix="-mwo_hood_light")

    @override
    @property
    def is_on(self) -> bool | None:
        """Return true if the hood light is on."""
        level = self._appliance.get_hood_light_level()
        if level is None:
            return None
        return level != HoodLightLevel.Off

    @override
    @property
    def brightness(self) -> int | None:
        """Return the brightness of the hood light."""
        level = self._appliance.get_hood_light_level()
        if level is None:
            return None
        return _LEVEL_TO_BRIGHTNESS.get(level, 0)

    @override
    @property
    def effect(self) -> str | None:
        """Return the current color effect."""
        color = self._appliance.get_hood_light_color()
        if color is None:
            return None
        return _COLOR_TO_EFFECT.get(color)

    @override
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the hood light on."""
        if ATTR_BRIGHTNESS in kwargs:
            level = _brightness_to_level(kwargs[ATTR_BRIGHTNESS])
            MicrowaveHoodLight._check_service_request(
                await self._appliance.set_hood_light_level(level)
            )
        elif not self.is_on:
            # Default to High when turning on without brightness.
            MicrowaveHoodLight._check_service_request(
                await self._appliance.set_hood_light_level(HoodLightLevel.High)
            )

        if ATTR_EFFECT in kwargs:
            color = _COLOR_EFFECTS.get(kwargs[ATTR_EFFECT])
            if color is not None:
                MicrowaveHoodLight._check_service_request(
                    await self._appliance.set_hood_light_color(color)
                )

    @override
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the hood light off."""
        MicrowaveHoodLight._check_service_request(
            await self._appliance.set_hood_light_level(HoodLightLevel.Off)
        )
