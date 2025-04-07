"""
This component provides light support for Buspro.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/...
"""

import asyncio
import logging

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.components.light import (
    LightEntity, 
    ColorMode, 
    PLATFORM_SCHEMA, 
    ATTR_BRIGHTNESS
)
from homeassistant.const import (CONF_NAME, CONF_DEVICES, CONF_SCAN_INTERVAL)
from homeassistant.core import callback
from .pybuspro.devices import Light
from custom_components.buspro.helpers import wait_for_buspro

from ..buspro import DATA_BUSPRO

_LOGGER = logging.getLogger(__name__)

DEFAULT_DEVICE_RUNNING_TIME = 0
DEFAULT_PLATFORM_RUNNING_TIME = 0
DEFAULT_DIMMABLE = True

DEVICE_SCHEMA = vol.Schema({
    vol.Optional("running_time", default=DEFAULT_DEVICE_RUNNING_TIME): cv.positive_int,
    vol.Optional("dimmable", default=DEFAULT_DIMMABLE): cv.boolean,
    vol.Optional(CONF_SCAN_INTERVAL, default=0): cv.positive_int,
    vol.Required(CONF_NAME): cv.string,
})

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional("running_time", default=DEFAULT_PLATFORM_RUNNING_TIME): cv.positive_int,
    vol.Required(CONF_DEVICES): {cv.string: DEVICE_SCHEMA},
})


# noinspection PyUnusedLocal
async def async_setup_platform(hass, config, async_add_entites, discovery_info=None):
    """Set up Buspro light devices."""

    if not await wait_for_buspro(hass):
        return False
    
    devices = []
    platform_running_time = int(config["running_time"])

    for address, device_config in config[CONF_DEVICES].items():
        name = device_config[CONF_NAME]
        scan_interval = device_config[CONF_SCAN_INTERVAL]
        device_running_time = int(device_config["running_time"])
        dimmable = bool(device_config["dimmable"])

        if device_running_time == 0:
            device_running_time = platform_running_time
        if dimmable:
            device_running_time = 0

        address2 = address.split('.')
        device_address = (int(address2[0]), int(address2[1]))
        channel_number = int(address2[2])
        if _LOGGER.isEnabledFor(logging.DEBUG):
            _LOGGER.debug("Adding light '{}' with address {} and channel number {}".format(name, device_address, channel_number))

        light = Light(hass, device_address, channel_number, name)
        devices.append(BusproLight(hass, light, device_running_time, dimmable,scan_interval))

    async_add_entites(devices)


# noinspection PyAbstractClass
class BusproLight(LightEntity):
    """Representation of a Buspro light."""

    def __init__(self, hass, device, running_time, dimmable, scan_interval):
        self._hass = hass
        self._device = device
        self._running_time = running_time
        self._dimmable = dimmable
        self._scan_interval = scan_interval
        self.async_register_callbacks()

    @property
    def supported_color_modes(self) -> set:
        """Return supported color modes."""
        return {ColorMode.BRIGHTNESS} if self._dimmable else {ColorMode.ONOFF}

    @property
    def color_mode(self) -> str:
        """Return the color mode of the light."""
        return ColorMode.BRIGHTNESS if self._dimmable else ColorMode.ONOFF

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        if _LOGGER.isEnabledFor(logging.DEBUG):
            _LOGGER.debug("Added light '{}' scan interval {}".format(self._device.name, self.scan_interval))
        await self._hass.data[DATA_BUSPRO].entity_initialized(self)

    @callback
    def async_register_callbacks(self):
        """Register callbacks to update hass after device was changed."""
        
        async def after_update_callback(device, should_reschedule=True):
            """Call after device was updated."""
            self.async_write_ha_state()
            await self._hass.data[DATA_BUSPRO].scheduler.device_updated(self.entity_id)

        self._device.register_device_updated_cb(after_update_callback)

    @property
    def should_poll(self):
        """No polling needed within Buspro."""
        return False

    async def async_update(self):
        await self._device.read_status()

    @property
    def name(self):
        """Return the display name of this light."""
        return self._device.name

    @property
    def available(self):
        """Return True if entity is available."""
        return self._hass.data[DATA_BUSPRO].connected

    @property
    def brightness(self):
        """Return the brightness of the light."""
        brightness = self._device.current_brightness / 100 * 255
        return brightness

    @property
    def is_on(self):
        """Return true if light is on."""
        return self._device.is_on

    @property
    def scan_interval(self):
        """Return the scan interval of the light."""
        return self._scan_interval

    async def async_turn_on(self, **kwargs):
        """Instruct the light to turn on."""
        brightness = int(kwargs.get(ATTR_BRIGHTNESS, 255) / 255 * 100)

        if not self.is_on and self._device.previous_brightness is not None and brightness == 100:
            brightness = self._device.previous_brightness

        await self._device.set_brightness(brightness, self._running_time)

    async def async_turn_off(self, **kwargs):
        """Instruct the light to turn off."""
        await self._device.set_off(self._running_time)

    @property
    def unique_id(self):
        """Return unique ID for this light."""
        subnet, device = self._device._device_address
        channel = getattr(self._device, "_channel_number", "N")
        return f"{subnet}-{device}-{channel}-light"

