"""Config flow for the Google Keep integration."""
from __future__ import annotations

import logging
import uuid
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .api import GoogleKeepAPI
from .const import (
    CONF_AUTO_SYNC,
    CONF_COLOR_FILTER,
    CONF_DEFAULT_LIST,
    CONF_DEVICE_ID,
    CONF_LABEL_FILTER,
    CONF_MASTER_TOKEN,
    CONF_SHOW_ARCHIVED,
    CONF_SHOW_TRASHED,
    CONF_UPDATE_INTERVAL,
    DEFAULT_AUTO_SYNC,
    DEFAULT_SHOW_ARCHIVED,
    DEFAULT_SHOW_TRASHED,
    DEFAULT_UPDATE_INTERVAL_MINUTES,
    DOMAIN,
    LOGGER_NAME,
    MANUAL_UPDATE_INTERVAL,
    UPDATE_INTERVAL_OPTIONS,
    VALID_COLORS,
)
from .exceptions import GoogleKeepAuthError, GoogleKeepConnectionError

_LOGGER = logging.getLogger(LOGGER_NAME)

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_EMAIL): str,
        vol.Optional(CONF_PASSWORD): str,
        vol.Optional(CONF_MASTER_TOKEN): str,
        vol.Optional(CONF_DEVICE_ID): str,
    }
)


async def _validate_and_get_token(hass, user_input: dict[str, Any]) -> str:
    """Attempt a login, raising GoogleKeepAuthError/GoogleKeepConnectionError on failure."""
    device_id = user_input.get(CONF_DEVICE_ID) or uuid.uuid4().hex
    api = GoogleKeepAPI(
        hass,
        email=user_input[CONF_EMAIL],
        password=user_input.get(CONF_PASSWORD),
        master_token=user_input.get(CONF_MASTER_TOKEN),
        device_id=device_id,
    )
    token = await api.async_test_credentials()
    return token


class GoogleKeepConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Google Keep."""

    VERSION = 1

    def __init__(self) -> None:
        self._reauth_entry: ConfigEntry | None = None
        self._data: dict[str, Any] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            if not user_input.get(CONF_PASSWORD) and not user_input.get(
                CONF_MASTER_TOKEN
            ):
                errors["base"] = "missing_credentials"
            else:
                await self.async_set_unique_id(user_input[CONF_EMAIL].lower())
                self._abort_if_unique_id_configured()
                try:
                    token = await _validate_and_get_token(self.hass, user_input)
                except GoogleKeepAuthError:
                    errors["base"] = "invalid_auth"
                except GoogleKeepConnectionError:
                    errors["base"] = "cannot_connect"
                except Exception:  # noqa: BLE001
                    _LOGGER.exception("Unexpected error during Google Keep login")
                    errors["base"] = "unknown"
                else:
                    data = {**user_input, CONF_MASTER_TOKEN: token}
                    data.pop(CONF_PASSWORD, None)
                    return self.async_create_entry(
                        title=user_input[CONF_EMAIL], data=data
                    )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_SCHEMA, errors=errors
        )

    async def async_step_reauth(
        self, entry_data: dict[str, Any]
    ) -> ConfigFlowResult:
        """Start a reauth flow when the stored token stops working."""
        self._reauth_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )
        self._data = dict(entry_data)
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            merged = {**self._data, **user_input}
            try:
                token = await _validate_and_get_token(self.hass, merged)
            except GoogleKeepAuthError:
                errors["base"] = "invalid_auth"
            except GoogleKeepConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected error during Google Keep reauth")
                errors["base"] = "unknown"
            else:
                merged[CONF_MASTER_TOKEN] = token
                merged.pop(CONF_PASSWORD, None)
                assert self._reauth_entry is not None
                return self.async_update_reload_and_abort(
                    self._reauth_entry, data=merged
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
            description_placeholders={"email": self._data.get(CONF_EMAIL, "")},
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Let the user update email/password/token/device id post-setup."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                token = await _validate_and_get_token(self.hass, user_input)
            except GoogleKeepAuthError:
                errors["base"] = "invalid_auth"
            except GoogleKeepConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected error during Google Keep reconfigure")
                errors["base"] = "unknown"
            else:
                data = {**user_input, CONF_MASTER_TOKEN: token}
                data.pop(CONF_PASSWORD, None)
                return self.async_update_reload_and_abort(
                    entry, data=data, unique_id=user_input[CONF_EMAIL].lower()
                )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(
                STEP_USER_SCHEMA, entry.data
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return GoogleKeepOptionsFlow()


class GoogleKeepOptionsFlow(OptionsFlow):
    """Handle the Google Keep options flow (runtime preferences)."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            # The interval selector yields a string value; normalize to int.
            if CONF_UPDATE_INTERVAL in user_input:
                user_input[CONF_UPDATE_INTERVAL] = int(user_input[CONF_UPDATE_INTERVAL])
            return self.async_create_entry(data=user_input)

        current = self.config_entry.options
        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_UPDATE_INTERVAL,
                    default=current.get(
                        CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL_MINUTES
                    ),
                ): SelectSelector(
                    SelectSelectorConfig(
                        options=[
                            SelectOptionDict(value=str(MANUAL_UPDATE_INTERVAL), label="manual"),
                            *[
                                SelectOptionDict(value=str(m), label=f"{m} min")
                                for m in UPDATE_INTERVAL_OPTIONS
                            ],
                        ],
                        mode=SelectSelectorMode.DROPDOWN,
                        translation_key="update_interval",
                    )
                ),
                vol.Optional(
                    CONF_AUTO_SYNC,
                    default=current.get(CONF_AUTO_SYNC, DEFAULT_AUTO_SYNC),
                ): bool,
                vol.Optional(
                    CONF_DEFAULT_LIST,
                    default=current.get(CONF_DEFAULT_LIST, ""),
                ): str,
                vol.Optional(
                    CONF_SHOW_ARCHIVED,
                    default=current.get(CONF_SHOW_ARCHIVED, DEFAULT_SHOW_ARCHIVED),
                ): bool,
                vol.Optional(
                    CONF_SHOW_TRASHED,
                    default=current.get(CONF_SHOW_TRASHED, DEFAULT_SHOW_TRASHED),
                ): bool,
                vol.Optional(
                    CONF_LABEL_FILTER,
                    default=current.get(CONF_LABEL_FILTER, []),
                ): SelectSelector(
                    SelectSelectorConfig(options=[], custom_value=True, multiple=True)
                ),
                vol.Optional(
                    CONF_COLOR_FILTER,
                    default=current.get(CONF_COLOR_FILTER, []),
                ): SelectSelector(
                    SelectSelectorConfig(
                        options=[SelectOptionDict(value=c, label=c) for c in VALID_COLORS],
                        multiple=True,
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                ),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
