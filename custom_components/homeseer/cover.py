"""Support for HomeSeer cover-type devices."""

import logging

from homeassistant.components.cover import (
    CoverEntity,
    ATTR_POSITION,
    DEVICE_CLASS_BLIND,
    DEVICE_CLASS_GARAGE,
    SUPPORT_CLOSE,
    SUPPORT_OPEN,
    SUPPORT_STOP,
    SUPPORT_SET_POSITION,
)

from .const import DOMAIN
from .homeseer import HomeSeerEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up HomeSeer cover-type devices."""
    cover_entities = []
    bridge = hass.data[DOMAIN]

    for device in bridge.devices["cover"]:
        if hasattr(device, "dim"):
            """Device is a blind."""
            entity = HomeSeerBlind(device, bridge)
            cover_entities.append(entity)
            _LOGGER.info(
                f"Added HomeSeer blind-type device: {entity.name} ({entity.device_state_attributes})"
            )
        else:
            """Device is a garage-door opener."""
            entity = HomeSeerGarageDoor(device, bridge)
            cover_entities.append(entity)
            _LOGGER.info(
                f"Added HomeSeer garage-type device: {entity.name} ({entity.device_state_attributes})"
            )

    if cover_entities:
        async_add_entities(cover_entities)


class HomeSeerCover(HomeSeerEntity, CoverEntity):
    """Base representation for a HomeSeer cover entity."""

    async def async_open_cover(self, **kwargs):
        await self._device.off()

    async def async_close_cover(self, **kwargs):
        await self._device.on()

class HomeSeerGarageDoor(HomeSeerCover):
    """Representation of a garage door opener device."""

    @property
    def supported_features(self):
        """Return the features supported by the device."""
        return SUPPORT_OPEN | SUPPORT_CLOSE

    @property
    def device_class(self):
        """Return the device class for the device."""
        return DEVICE_CLASS_GARAGE

    @property
    def is_opening(self):
        """Return if the cover is opening or not."""
        return self._device.status == "Opening"

    @property
    def is_closing(self):
        """Return if the cover is closing or not."""
        return self._device.status == "Closing"

    @property
    def is_closed(self):
        """Return if the cover is closed or not."""
        return self._device.status == "Closed"


class HomeSeerBlind(HomeSeerCover):
    """Representation of a window-covering device."""

    @property
    def supported_features(self):
        """Return the features supported by the device."""
        if self._device.dim_supported:
            return SUPPORT_OPEN | SUPPORT_CLOSE | SUPPORT_SET_POSITION | SUPPORT_STOP
        else: 
            return SUPPORT_OPEN | SUPPORT_CLOSE | SUPPORT_STOP

    @property
    def device_class(self):
        """Return the device class for the device."""
        return DEVICE_CLASS_BLIND

    @property
    def current_cover_position(self):
        if self._device.dim_supported:
            """Return the current position of the cover."""
            return self._device.dim_percent
        return None

    @property
    def is_closed(self):
        return None

    async def async_set_cover_position(self, **kwargs):
        if self._device.dim_supported:
            await self._device.dim(kwargs.get(ATTR_POSITION, 0))
    
    async def async_stop_cover(self, **kwargs):
        await self._device.stop()
