"""Binary sensors for Whirlpool Appliances (AWS IoT)."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import timedelta

from whirlpool.appliance import Appliance
from whirlpool.microwave import Microwave

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import WhirlpoolConfigEntry
from .entity import WhirlpoolEntity

PARALLEL_UPDATES = 1
SCAN_INTERVAL = timedelta(minutes=5)


@dataclass(frozen=True, kw_only=True)
class WhirlpoolBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describes a Whirlpool binary sensor entity."""

    value_fn: Callable[[Appliance], bool | None]


WASHER_DRYER_SENSORS: list[WhirlpoolBinarySensorEntityDescription] = [
    WhirlpoolBinarySensorEntityDescription(
        key="door",
        device_class=BinarySensorDeviceClass.DOOR,
        value_fn=lambda appliance: appliance.get_door_open(),
    )
]

MICROWAVE_BINARY_SENSORS: list[WhirlpoolBinarySensorEntityDescription] = [
    WhirlpoolBinarySensorEntityDescription(
        key="mwo_door_locked",
        translation_key="microwave_door_locked",
        device_class=BinarySensorDeviceClass.LOCK,
        value_fn=lambda mwo: mwo.get_door_locked(),
    ),
    WhirlpoolBinarySensorEntityDescription(
        key="mwo_remote_start",
        translation_key="microwave_remote_start",
        value_fn=lambda mwo: mwo.get_remote_start_enabled(),
    ),
    WhirlpoolBinarySensorEntityDescription(
        key="mwo_turntable",
        translation_key="microwave_turntable",
        value_fn=lambda mwo: mwo.get_turntable_enabled(),
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: WhirlpoolConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Config flow entry for Whirlpool binary sensors."""
    appliances_manager = config_entry.runtime_data

    entities: list[BinarySensorEntity] = []

    for washer in appliances_manager.washers:
        for description in WASHER_DRYER_SENSORS:
            entities.append(WhirlpoolBinarySensor(washer, description))

    for dryer in appliances_manager.dryers:
        for description in WASHER_DRYER_SENSORS:
            entities.append(WhirlpoolBinarySensor(dryer, description))

    for mwo in appliances_manager.microwaves:
        for description in MICROWAVE_BINARY_SENSORS:
            entities.append(WhirlpoolBinarySensor(mwo, description))

    async_add_entities(entities)


class WhirlpoolBinarySensor(WhirlpoolEntity, BinarySensorEntity):
    """A class for the Whirlpool binary sensors."""

    def __init__(
        self, appliance: Appliance, description: WhirlpoolBinarySensorEntityDescription
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(appliance, unique_id_suffix=f"-{description.key}")
        self.entity_description: WhirlpoolBinarySensorEntityDescription = description

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        return self.entity_description.value_fn(self._appliance)
