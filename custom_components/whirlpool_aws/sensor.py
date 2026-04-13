"""Sensors for Whirlpool Appliances (AWS IoT)."""

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import override

from whirlpool_aws.appliance import Appliance
from whirlpool_aws.dryer import Dryer, MachineState as DryerMachineState
from whirlpool_aws.microwave import Microwave, MicrowaveCavityState, MicrowaveDoorStatus
from whirlpool_aws.oven import (
    Cavity as OvenCavity,
    CavityState as OvenCavityState,
    CookMode,
    Oven,
)
from whirlpool_aws.washer import MachineState as WasherMachineState, Washer

from homeassistant.components.sensor import (
    RestoreSensor,
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.util.dt import utcnow

from . import WhirlpoolConfigEntry
from .entity import WhirlpoolEntity, WhirlpoolOvenEntity

PARALLEL_UPDATES = 1
SCAN_INTERVAL = timedelta(minutes=5)

WASHER_TANK_FILL = {
    0: None,
    1: "empty",
    2: "25",
    3: "50",
    4: "100",
    5: "active",
}

WASHER_MACHINE_STATE = {
    WasherMachineState.Standby: "standby",
    WasherMachineState.Setting: "setting",
    WasherMachineState.DelayCountdownMode: "delay_countdown",
    WasherMachineState.DelayPause: "delay_paused",
    WasherMachineState.SmartDelay: "smart_delay",
    WasherMachineState.SmartGridPause: "smart_grid_pause",
    WasherMachineState.Pause: "pause",
    WasherMachineState.RunningMainCycle: "running_maincycle",
    WasherMachineState.RunningPostCycle: "running_postcycle",
    WasherMachineState.Exceptions: "exception",
    WasherMachineState.Complete: "complete",
    WasherMachineState.PowerFailure: "power_failure",
    WasherMachineState.ServiceDiagnostic: "service_diagnostic_mode",
    WasherMachineState.FactoryDiagnostic: "factory_diagnostic_mode",
    WasherMachineState.LifeTest: "life_test",
    WasherMachineState.CustomerFocusMode: "customer_focus_mode",
    WasherMachineState.DemoMode: "demo_mode",
    WasherMachineState.HardStopOrError: "hard_stop_or_error",
    WasherMachineState.SystemInit: "system_initialize",
}

DRYER_MACHINE_STATE = {
    DryerMachineState.Standby: "standby",
    DryerMachineState.Setting: "setting",
    DryerMachineState.DelayCountdownMode: "delay_countdown",
    DryerMachineState.DelayPause: "delay_paused",
    DryerMachineState.SmartDelay: "smart_delay",
    DryerMachineState.SmartGridPause: "smart_grid_pause",
    DryerMachineState.Pause: "pause",
    DryerMachineState.RunningMainCycle: "running_maincycle",
    DryerMachineState.RunningPostCycle: "running_postcycle",
    DryerMachineState.Exceptions: "exception",
    DryerMachineState.Complete: "complete",
    DryerMachineState.PowerFailure: "power_failure",
    DryerMachineState.ServiceDiagnostic: "service_diagnostic_mode",
    DryerMachineState.FactoryDiagnostic: "factory_diagnostic_mode",
    DryerMachineState.LifeTest: "life_test",
    DryerMachineState.CustomerFocusMode: "customer_focus_mode",
    DryerMachineState.DemoMode: "demo_mode",
    DryerMachineState.HardStopOrError: "hard_stop_or_error",
    DryerMachineState.SystemInit: "system_initialize",
    DryerMachineState.Cancelled: "cancelled",
}

STATE_CYCLE_FILLING = "cycle_filling"
STATE_CYCLE_RINSING = "cycle_rinsing"
STATE_CYCLE_SENSING = "cycle_sensing"
STATE_CYCLE_SOAKING = "cycle_soaking"
STATE_CYCLE_SPINNING = "cycle_spinning"
STATE_CYCLE_WASHING = "cycle_washing"

OVEN_CAVITY_STATE = {
    OvenCavityState.Standby: "standby",
    OvenCavityState.Preheating: "preheating",
    OvenCavityState.Cooking: "cooking",
}

OVEN_COOK_MODE = {
    CookMode.Standby: "standby",
    CookMode.Bake: "bake",
    CookMode.ConvectBake: "convection_bake",
    CookMode.Broil: "broil",
    CookMode.ConvectBroil: "convection_broil",
    CookMode.ConvectRoast: "convection_roast",
    CookMode.KeepWarm: "keep_warm",
    CookMode.AirFry: "air_fry",
}

MICROWAVE_CAVITY_STATE = {
    MicrowaveCavityState.Idle: "idle",
    MicrowaveCavityState.Cooking: "cooking",
    MicrowaveCavityState.Paused: "paused",
    MicrowaveCavityState.Completed: "completed",
    MicrowaveCavityState.TurningOff: "turning_off",
    MicrowaveCavityState.Unknown: "unknown",
}

MICROWAVE_DOOR_STATUS = {
    MicrowaveDoorStatus.Open: "open",
    MicrowaveDoorStatus.Closed: "closed",
    MicrowaveDoorStatus.Unknown: "unknown",
}


def washer_state(washer: Washer) -> str | None:
    """Determine correct states for a washer."""
    machine_state = washer.get_machine_state()

    if machine_state == WasherMachineState.RunningMainCycle:
        if washer.get_cycle_status_filling():
            return STATE_CYCLE_FILLING
        if washer.get_cycle_status_rinsing():
            return STATE_CYCLE_RINSING
        if washer.get_cycle_status_sensing():
            return STATE_CYCLE_SENSING
        if washer.get_cycle_status_soaking():
            return STATE_CYCLE_SOAKING
        if washer.get_cycle_status_spinning():
            return STATE_CYCLE_SPINNING
        if washer.get_cycle_status_washing():
            return STATE_CYCLE_WASHING

    return WASHER_MACHINE_STATE.get(machine_state)


def dryer_state(dryer: Dryer) -> str | None:
    """Determine correct states for a dryer."""
    machine_state = dryer.get_machine_state()

    if machine_state == DryerMachineState.RunningMainCycle:
        if dryer.get_cycle_status_sensing():
            return STATE_CYCLE_SENSING

    return DRYER_MACHINE_STATE.get(machine_state)


@dataclass(frozen=True, kw_only=True)
class WhirlpoolSensorEntityDescription(SensorEntityDescription):
    """Describes a Whirlpool sensor entity."""

    value_fn: Callable[[Appliance], str | None]


WASHER_STATE_OPTIONS = [
    *WASHER_MACHINE_STATE.values(),
    STATE_CYCLE_FILLING,
    STATE_CYCLE_RINSING,
    STATE_CYCLE_SENSING,
    STATE_CYCLE_SOAKING,
    STATE_CYCLE_SPINNING,
    STATE_CYCLE_WASHING,
]

DRYER_STATE_OPTIONS = [
    *DRYER_MACHINE_STATE.values(),
    STATE_CYCLE_SENSING,
]

WASHER_SENSORS: tuple[WhirlpoolSensorEntityDescription, ...] = (
    WhirlpoolSensorEntityDescription(
        key="state",
        translation_key="washer_state",
        device_class=SensorDeviceClass.ENUM,
        options=WASHER_STATE_OPTIONS,
        value_fn=washer_state,
    ),
    WhirlpoolSensorEntityDescription(
        key="DispenseLevel",
        translation_key="whirlpool_tank",
        entity_registry_enabled_default=False,
        device_class=SensorDeviceClass.ENUM,
        options=[value for value in WASHER_TANK_FILL.values() if value],
        value_fn=lambda washer: WASHER_TANK_FILL.get(washer.get_dispense_1_level()),
    ),
)

DRYER_SENSORS: tuple[WhirlpoolSensorEntityDescription, ...] = (
    WhirlpoolSensorEntityDescription(
        key="state",
        translation_key="dryer_state",
        device_class=SensorDeviceClass.ENUM,
        options=DRYER_STATE_OPTIONS,
        value_fn=dryer_state,
    ),
)

WASHER_DRYER_TIME_SENSORS: tuple[SensorEntityDescription] = (
    SensorEntityDescription(
        key="timeremaining",
        translation_key="end_time",
        device_class=SensorDeviceClass.TIMESTAMP,
        icon="mdi:progress-clock",
    ),
)

MICROWAVE_SENSORS: tuple[WhirlpoolSensorEntityDescription, ...] = (
    WhirlpoolSensorEntityDescription(
        key="mwo_cavity_state",
        translation_key="microwave_cavity_state",
        device_class=SensorDeviceClass.ENUM,
        options=list(MICROWAVE_CAVITY_STATE.values()),
        value_fn=lambda mwo: MICROWAVE_CAVITY_STATE.get(mwo.get_cavity_state()),
    ),
    WhirlpoolSensorEntityDescription(
        key="mwo_door_status",
        translation_key="microwave_door_status",
        device_class=SensorDeviceClass.ENUM,
        options=list(MICROWAVE_DOOR_STATUS.values()),
        value_fn=lambda mwo: MICROWAVE_DOOR_STATUS.get(mwo.get_door_status()),
    ),
    WhirlpoolSensorEntityDescription(
        key="mwo_power_level",
        translation_key="microwave_power_level",
        value_fn=lambda mwo: str(val) if (val := mwo.get_mwo_power_level()) is not None else None,
    ),
    WhirlpoolSensorEntityDescription(
        key="mwo_timer_remaining",
        translation_key="microwave_timer_remaining",
        native_unit_of_measurement=UnitOfTime.SECONDS,
        device_class=SensorDeviceClass.DURATION,
        value_fn=lambda mwo: str(val) if (val := mwo.get_cook_timer_remaining_seconds()) is not None else None,
    ),
    WhirlpoolSensorEntityDescription(
        key="mwo_timer_state",
        translation_key="microwave_timer_state",
        value_fn=lambda mwo: mwo.get_cook_timer_state(),
    ),
    WhirlpoolSensorEntityDescription(
        key="mwo_active_recipe",
        translation_key="microwave_active_recipe",
        value_fn=lambda mwo: mwo.get_active_recipe_id(),
    ),
)


@dataclass(frozen=True, kw_only=True)
class WhirlpoolMicrowaveTempSensorDescription(SensorEntityDescription):
    """Describes a Whirlpool microwave temperature sensor."""

    value_fn: Callable[[Microwave], float | None]
    unit_fn: Callable[[Microwave], str | None]


MICROWAVE_TEMP_SENSOR = WhirlpoolMicrowaveTempSensorDescription(
    key="mwo_display_temp",
    translation_key="microwave_display_temperature",
    device_class=SensorDeviceClass.TEMPERATURE,
    state_class=SensorStateClass.MEASUREMENT,
    value_fn=lambda mwo: mwo.get_display_temperature(),
    unit_fn=lambda mwo: mwo.get_display_temperature_unit(),
)


@dataclass(frozen=True, kw_only=True)
class WhirlpoolOvenCavitySensorEntityDescription(SensorEntityDescription):
    """Describes a Whirlpool oven cavity sensor entity."""

    value_fn: Callable[[Oven, OvenCavity], str | int | float | None]


OVEN_CAVITY_SENSORS: tuple[WhirlpoolOvenCavitySensorEntityDescription, ...] = (
    WhirlpoolOvenCavitySensorEntityDescription(
        key="oven_state",
        translation_key="oven_state",
        device_class=SensorDeviceClass.ENUM,
        options=list(OVEN_CAVITY_STATE.values()),
        value_fn=lambda oven, cavity: (
            OVEN_CAVITY_STATE.get(state)
            if (state := oven.get_cavity_state(cavity)) is not None
            else None
        ),
    ),
    WhirlpoolOvenCavitySensorEntityDescription(
        key="oven_cook_mode",
        translation_key="oven_cook_mode",
        device_class=SensorDeviceClass.ENUM,
        options=list(OVEN_COOK_MODE.values()),
        value_fn=lambda oven, cavity: (
            OVEN_COOK_MODE.get(cook_mode)
            if (cook_mode := oven.get_cook_mode(cavity)) is not None
            else None
        ),
    ),
    WhirlpoolOvenCavitySensorEntityDescription(
        key="oven_current_temperature",
        translation_key="oven_current_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda oven, cavity: oven.get_temp(cavity),
    ),
    WhirlpoolOvenCavitySensorEntityDescription(
        key="oven_target_temperature",
        translation_key="oven_target_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda oven, cavity: oven.get_target_temp(cavity),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: WhirlpoolConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Config flow entry for Whirlpool sensors."""
    appliances_manager = config_entry.runtime_data

    entities: list[SensorEntity] = []

    # Washer sensors.
    for washer in appliances_manager.washers:
        for description in WASHER_SENSORS:
            entities.append(WhirlpoolSensor(washer, description))
        for description in WASHER_DRYER_TIME_SENSORS:
            entities.append(WasherTimeSensor(washer, description))

    # Dryer sensors.
    for dryer in appliances_manager.dryers:
        for description in DRYER_SENSORS:
            entities.append(WhirlpoolSensor(dryer, description))
        for description in WASHER_DRYER_TIME_SENSORS:
            entities.append(DryerTimeSensor(dryer, description))

    # Oven sensors.
    for oven in appliances_manager.ovens:
        for cavity in (OvenCavity.Upper, OvenCavity.Lower):
            if oven.get_oven_cavity_exists(cavity):
                for description in OVEN_CAVITY_SENSORS:
                    entities.append(
                        WhirlpoolOvenCavitySensor(oven, cavity, description)
                    )

    # Microwave sensors.
    for mwo in appliances_manager.microwaves:
        for description in MICROWAVE_SENSORS:
            entities.append(WhirlpoolSensor(mwo, description))
        entities.append(MicrowaveTempSensor(mwo, MICROWAVE_TEMP_SENSOR))

    async_add_entities(entities)


class WhirlpoolSensor(WhirlpoolEntity, SensorEntity):
    """A class for the Whirlpool sensors."""

    def __init__(
        self, appliance: Appliance, description: WhirlpoolSensorEntityDescription
    ) -> None:
        """Initialize the sensor."""
        super().__init__(appliance, unique_id_suffix=f"-{description.key}")
        self.entity_description: WhirlpoolSensorEntityDescription = description

    @property
    def native_value(self) -> StateType | str:
        """Return native value of sensor."""
        return self.entity_description.value_fn(self._appliance)


class MicrowaveTempSensor(WhirlpoolEntity, SensorEntity):
    """Microwave temperature sensor with dynamic unit."""

    def __init__(
        self,
        appliance: Microwave,
        description: WhirlpoolMicrowaveTempSensorDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(appliance, unique_id_suffix=f"-{description.key}")
        self.entity_description: WhirlpoolMicrowaveTempSensorDescription = description
        self._microwave = appliance

    @property
    def native_value(self) -> float | None:
        """Return native value of sensor."""
        return self.entity_description.value_fn(self._microwave)

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Return dynamic unit based on appliance setting."""
        unit = self.entity_description.unit_fn(self._microwave)
        if unit == "F":
            return UnitOfTemperature.FAHRENHEIT
        if unit == "C":
            return UnitOfTemperature.CELSIUS
        return None


class WasherDryerTimeSensorBase(WhirlpoolEntity, RestoreSensor, ABC):
    """Abstract base class for Whirlpool washer/dryer time sensors."""

    _attr_should_poll = True
    _appliance: Washer | Dryer

    def __init__(
        self, appliance: Washer | Dryer, description: SensorEntityDescription
    ) -> None:
        """Initialize the washer/dryer sensor."""
        super().__init__(appliance, unique_id_suffix=f"-{description.key}")
        self.entity_description = description

        self._running: bool | None = None
        self._value: datetime | None = None

    @abstractmethod
    def _is_machine_state_finished(self) -> bool:
        """Return true if the machine is in a finished state."""

    @abstractmethod
    def _is_machine_state_running(self) -> bool:
        """Return true if the machine is in a running state."""

    async def async_added_to_hass(self) -> None:
        """Register attribute updates callback."""
        if restored_data := await self.async_get_last_sensor_data():
            if isinstance(restored_data.native_value, datetime):
                self._value = restored_data.native_value
        await super().async_added_to_hass()

    async def async_update(self) -> None:
        """Update status of Whirlpool."""
        await self._appliance.fetch_data()

    @override
    @property
    def native_value(self) -> datetime | None:
        """Calculate the time stamp for completion."""
        now = utcnow()

        if self._is_machine_state_finished() and self._running:
            self._running = False
            self._value = now

        if self._is_machine_state_running():
            self._running = True
            new_timestamp = now + timedelta(
                seconds=self._appliance.get_time_remaining()
            )
            if self._value is None or (
                isinstance(self._value, datetime)
                and abs(new_timestamp - self._value) > timedelta(seconds=60)
            ):
                self._value = new_timestamp
        return self._value


class WasherTimeSensor(WasherDryerTimeSensorBase):
    """A timestamp class for Whirlpool washers."""

    _appliance: Washer

    def _is_machine_state_finished(self) -> bool:
        """Return true if the machine is in a finished state."""
        return self._appliance.get_machine_state() in {
            WasherMachineState.Complete,
            WasherMachineState.Standby,
        }

    def _is_machine_state_running(self) -> bool:
        """Return true if the machine is in a running state."""
        return (
            self._appliance.get_machine_state() is WasherMachineState.RunningMainCycle
        )


class DryerTimeSensor(WasherDryerTimeSensorBase):
    """A timestamp class for Whirlpool dryers."""

    _appliance: Dryer

    def _is_machine_state_finished(self) -> bool:
        """Return true if the machine is in a finished state."""
        return self._appliance.get_machine_state() in {
            DryerMachineState.Complete,
            DryerMachineState.Standby,
        }

    def _is_machine_state_running(self) -> bool:
        """Return true if the machine is in a running state."""
        return self._appliance.get_machine_state() is DryerMachineState.RunningMainCycle


class WhirlpoolOvenCavitySensor(WhirlpoolOvenEntity, SensorEntity):
    """A class for Whirlpool oven cavity sensors."""

    def __init__(
        self,
        oven: Oven,
        cavity: OvenCavity,
        description: WhirlpoolOvenCavitySensorEntityDescription,
    ) -> None:
        """Initialize the oven cavity sensor."""
        super().__init__(
            oven, cavity, description.translation_key, f"-{description.key}"
        )
        self.entity_description: WhirlpoolOvenCavitySensorEntityDescription = (
            description
        )

    @property
    def native_value(self) -> StateType:
        """Return native value of sensor."""
        return self.entity_description.value_fn(self._appliance, self.cavity)
