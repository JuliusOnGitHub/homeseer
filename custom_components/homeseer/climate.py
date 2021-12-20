"""Support for HomeSeer light-type devices."""

import logging

from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    ATTR_HVAC_MODE,
    DEFAULT_MAX_TEMP,
    DEFAULT_MIN_TEMP,
    HVAC_MODE_COOL,
    HVAC_MODE_DRY,
    HVAC_MODE_FAN_ONLY,
    HVAC_MODE_HEAT,
    HVAC_MODE_HEAT_COOL,
    HVAC_MODE_OFF,
    SUPPORT_FAN_MODE,
    SUPPORT_SWING_MODE,
    SUPPORT_TARGET_TEMPERATURE,
)

from homeassistant.const import ATTR_TEMPERATURE, TEMP_CELSIUS

from .libhomeseer.devices import (
    CONTROL_USE_THERM_MODE_OFF,
    CONTROL_USE_THERM_MODE_HEAT,
    CONTROL_USE_THERM_MODE_COOL,
)

from .const import DOMAIN
from .homeseer import HomeSeerEntity


_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up HomeSeer thermostat-type devices."""
    climate_entites = []
    bridge = hass.data[DOMAIN]

    _LOGGER.info("Adding HomeSeer Climate sensor")
    for device in bridge.devices["climate"]:
        entity = HomeSeerClimate(device, bridge)
        climate_entites.append(entity)
        _LOGGER.info(
            f"Added HomeSeer thermostat-type device: {entity.name} ({entity.device_state_attributes})"
        )

    if climate_entites:
        async_add_entities(climate_entites)


class HomeSeerClimate(HomeSeerEntity, ClimateEntity):
    """Representation of a HomeSeer light-type device."""

    @property
    def temperature_unit(self):
        return TEMP_CELSIUS

    @property
    def current_temperature(self) -> float:
        if self._device._temp is not None:
            return self._device._temp.value
        return 0

    @property
    def target_temperature(self) -> float:
        if self.hvac_mode == "Heat":
            return self.target_temperature_high
        return self.target_temperature_low

    @property
    def target_temperature_high(self) -> float:
        if self._device._heating_setpoint is not None:
            return self._device._heating_setpoint.value
        return 0

    @property
    def target_temperature_low(self) -> float:
        if self._device._cooling_setpoint is not None:
            return self._device._cooling_setpoint.value
        return 0

    @property
    def target_temperature_step(self) -> float:
        return 0.5

    @property
    def hvac_mode(self) -> str:
        if self._device._mode is not None:
            return self._device._mode.status
        return "Off"
    
    @property
    def is_heating(self) -> bool:
        return self._device._mode.value == HVAC_MODE_HEAT

    @property
    def hvac_action(self) -> str:
        if self._device._heater.is_on:
            return "Heating"
        return ""

    @property
    def hvac_modes(self):
        return [HVAC_MODE_OFF, HVAC_MODE_HEAT, HVAC_MODE_COOL]

    @property
    def supported_features(self):
        """Flag supported features."""
        return SUPPORT_TARGET_TEMPERATURE

    async def async_set_hvac_mode(self, hvac_mode):
        """Set new target hvac mode."""
        mode = self.convert_mode(hvac_mode)
        self._device._mode.set_value(mode)
    
    def convert_mode(self, hvac_mode) -> int:
        if hvac_mode == HVAC_MODE_HEAT:
            return CONTROL_USE_THERM_MODE_HEAT
        if hvac_mode == HVAC_MODE_COOL:
            return CONTROL_USE_THERM_MODE_COOL
        if hvac_mode == HVAC_MODE_OFF:
            return CONTROL_USE_THERM_MODE_OFF
        return CONTROL_USE_THERM_MODE_OFF

    async def async_set_temperature(self, **kwargs):
        if ATTR_TEMPERATURE in kwargs:
            if self.is_heating:
                await self._device._heating_setpoint(kwargs.get(ATTR_TEMPERATURE))
            else:
                await self._device._cooling_setpoint(kwargs.get(ATTR_TEMPERATURE))
