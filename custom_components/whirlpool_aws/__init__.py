"""The Whirlpool Appliances (AWS IoT) integration."""

import logging

import voluptuous as vol
from aiohttp import ClientError
from whirlpool.appliancesmanager import AppliancesManager
from whirlpool.auth import AccountLockedError as WhirlpoolAccountLocked, Auth
from whirlpool.backendselector import BackendSelector
from whirlpool.microwave import RecipeId

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_REGION, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import (
    ConfigEntryAuthFailed,
    ConfigEntryNotReady,
    HomeAssistantError,
)
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import BRANDS_CONF_MAP, CONF_BRAND, DOMAIN, REGIONS_CONF_MAP

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.CLIMATE,
    Platform.LIGHT,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
]

type WhirlpoolConfigEntry = ConfigEntry[AppliancesManager]

RECIPE_MAP = {
    "microwave": RecipeId.Microwave,
    "reheat": RecipeId.Reheat,
    "defrost": RecipeId.Defrost,
    "soften": RecipeId.Soften,
}


async def async_setup_entry(hass: HomeAssistant, entry: WhirlpoolConfigEntry) -> bool:
    """Set up Whirlpool AWS from a config entry."""
    session = async_get_clientsession(hass)
    region = REGIONS_CONF_MAP[entry.data.get(CONF_REGION, "EU")]
    brand = BRANDS_CONF_MAP[entry.data.get(CONF_BRAND, "Whirlpool")]
    backend_selector = BackendSelector(brand, region)

    auth = Auth(
        backend_selector, entry.data[CONF_USERNAME], entry.data[CONF_PASSWORD], session
    )
    try:
        await auth.do_auth(store=False)
    except (ClientError, TimeoutError) as ex:
        raise ConfigEntryNotReady(
            translation_domain=DOMAIN, translation_key="cannot_connect"
        ) from ex
    except WhirlpoolAccountLocked as ex:
        raise ConfigEntryAuthFailed(
            translation_domain=DOMAIN, translation_key="account_locked"
        ) from ex

    if not auth.is_access_token_valid():
        _LOGGER.error("Authentication failed")
        raise ConfigEntryAuthFailed(
            translation_domain=DOMAIN, translation_key="invalid_auth"
        )

    appliances_manager = AppliancesManager(backend_selector, auth, session)
    if not await appliances_manager.connect():
        raise ConfigEntryNotReady(
            translation_domain=DOMAIN, translation_key="appliances_fetch_failed"
        )

    entry.runtime_data = appliances_manager

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register start_microwave service.
    async def handle_start_microwave(call: ServiceCall) -> None:
        """Handle the start_microwave service call."""
        entity_id = call.data["entity_id"]
        recipe_str = call.data["recipe"]
        power_level = int(call.data["power_level"])
        duration = int(call.data["duration"])

        recipe = RECIPE_MAP.get(recipe_str)
        if recipe is None:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="invalid_recipe",
            )

        # Find the microwave appliance from the entity_id.
        ent_reg = er.async_get(hass)
        ent_entry = ent_reg.async_get(entity_id)
        if ent_entry is None:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="entity_not_found",
            )

        said = ent_entry.unique_id.split("-")[0] if ent_entry.unique_id else None
        microwave = None
        for mwo in appliances_manager.microwaves:
            if mwo.said == said:
                microwave = mwo
                break

        if microwave is None:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="microwave_not_found",
            )

        result = await microwave.start_cook(recipe, power_level, duration)
        if not result:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="remote_start_disabled",
            )

    if not hass.services.has_service(DOMAIN, "start_microwave"):
        hass.services.async_register(
            DOMAIN,
            "start_microwave",
            handle_start_microwave,
            schema=vol.Schema(
                {
                    vol.Required("entity_id"): str,
                    vol.Required("recipe"): vol.In(list(RECIPE_MAP.keys())),
                    vol.Required("power_level"): vol.All(
                        vol.Coerce(int), vol.Range(min=1, max=100)
                    ),
                    vol.Required("duration"): vol.All(
                        vol.Coerce(int), vol.Range(min=1, max=5400)
                    ),
                }
            ),
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: WhirlpoolConfigEntry) -> bool:
    """Unload a config entry."""
    await entry.runtime_data.disconnect()
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
