"""The Google Keep integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady

from .api import GoogleKeepAPI
from .const import (
    CONF_DEVICE_ID,
    CONF_MASTER_TOKEN,
    CONF_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL_MINUTES,
    DOMAIN,
    LOGGER_NAME,
)
from .coordinator import GoogleKeepCoordinator
from .exceptions import GoogleKeepAuthError, GoogleKeepConnectionError, GoogleKeepError
from .services import async_setup_services, async_unload_services

_LOGGER = logging.getLogger(LOGGER_NAME)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.TODO, Platform.BINARY_SENSOR]

type GoogleKeepConfigEntry = ConfigEntry[GoogleKeepCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: GoogleKeepConfigEntry) -> bool:
    """Set up Google Keep from a config entry."""
    api = GoogleKeepAPI(
        hass,
        email=entry.data[CONF_EMAIL],
        master_token=entry.data.get(CONF_MASTER_TOKEN),
        device_id=entry.data.get(CONF_DEVICE_ID),
    )

    try:
        await api.async_login()
    except GoogleKeepAuthError as err:
        raise ConfigEntryAuthFailed(str(err)) from err
    except GoogleKeepConnectionError as err:
        raise ConfigEntryNotReady(str(err)) from err
    except GoogleKeepError as err:
        raise ConfigEntryNotReady(str(err)) from err

    coordinator = GoogleKeepCoordinator(hass, entry, api)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    async_setup_services(hass)

    return True


async def _async_update_listener(hass: HomeAssistant, entry: GoogleKeepConfigEntry) -> None:
    """Reload the config entry when options change (interval, filters, ...)."""
    interval = entry.options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL_MINUTES)
    entry.runtime_data.set_update_interval(interval)
    await entry.runtime_data.async_request_refresh()


async def async_unload_entry(hass: HomeAssistant, entry: GoogleKeepConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        await entry.runtime_data.api.async_close()
        if not hass.config_entries.async_entries(DOMAIN):
            async_unload_services(hass)
    return unloaded
