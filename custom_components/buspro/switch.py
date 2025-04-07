"""
This component provides switch support for Buspro.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/...
"""

import asyncio
import logging

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.components.switch import SwitchEntity, PLATFORM_SCHEMA
from homeassistant.const import (CONF_NAME, CONF_DEVICES, CONF_SCAN_INTERVAL, CONF_DEVICE)
from homeassistant.core import callback

from custom_components.buspro.pybuspro.devices.switch import Switch
from custom_components.buspro.pybuspro.devices.panel import Panel
from custom_components.buspro.pybuspro.devices.universal_switch import UniversalSwitch
from .pybuspro.helpers.enums import DeviceFamily, SwitchType, validate_device_family

from ..buspro import DATA_BUSPRO
from .helpers import wait_for_buspro

DEFAULT_CONF_DEVICE = DeviceFamily.RELAY.value # Default device type
CONF_TYPE = "type"
DEFAULT_CONF_TYPE = SwitchType.RELAY.value  # Default switch type

SWITCH_TYPES = {
    SwitchType.RELAY.value: "Standard relay channel",
    SwitchType.UNIVERSAL_SWITCH.value: "Universal switch"
}

_LOGGER = logging.getLogger(__name__)

DEVICE_SCHEMA = vol.Schema({
    vol.Required(CONF_NAME): cv.string,
    vol.Optional(CONF_SCAN_INTERVAL, default=0): cv.positive_int,
    vol.Optional(CONF_DEVICE, default=DEFAULT_CONF_DEVICE): vol.All(cv.string, validate_device_family),
    vol.Optional(CONF_TYPE, default=DEFAULT_CONF_TYPE): vol.In(SWITCH_TYPES),
})

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_DEVICES): {cv.string: DEVICE_SCHEMA},
})


# noinspection PyUnusedLocal
async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up Buspro switch devices."""
    if not await wait_for_buspro(hass):
        return False        
    
    devices = []

    for address, device_config in config[CONF_DEVICES].items():
        name = device_config[CONF_NAME]
        scan_interval = device_config[CONF_SCAN_INTERVAL]
        device_type = device_config.get(CONF_DEVICE, DEFAULT_CONF_DEVICE)
        switch_type = device_config.get(CONF_TYPE, DEFAULT_CONF_TYPE)
        address2 = address.split('.')
        device_address = (int(address2[0]), int(address2[1]))

        if device_type == DeviceFamily.PANEL.value:
            channel_number = int(address2[2])
            if _LOGGER.isEnabledFor(logging.DEBUG):
                _LOGGER.debug(f"Adding panel switch '{name}' with address {device_address} and channel {channel_number}")
            device = Panel(hass, device_address, channel_number, name)
        else:  # relay device type
            if switch_type == SwitchType.UNIVERSAL_SWITCH.value:
                switch_number = int(address2[2])
                if _LOGGER.isEnabledFor(logging.DEBUG):
                    _LOGGER.debug(f"Adding universal switch '{name}' with address {device_address} and number {switch_number}")
                device = UniversalSwitch(hass, device_address, switch_number, name)
            else:  # relay switch type
                channel_number = int(address2[2])
                if _LOGGER.isEnabledFor(logging.DEBUG):
                    _LOGGER.debug(f"Adding relay switch '{name}' with address {device_address} and channel {channel_number}")
                device = Switch(hass, device_address, channel_number, name)

        devices.append(BusproSwitch(hass, device, scan_interval))

    async_add_entities(devices)



# noinspection PyAbstractClass
class BusproSwitch(SwitchEntity):
    def __init__(self, hass, device, scan_interval):
        self._scan_interval = 0
        self._hass = hass
        self._device = device
        self._scan_interval = scan_interval
        self.async_register_callbacks()

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        if _LOGGER.isEnabledFor(logging.DEBUG):
            _LOGGER.debug("Added switch '{}' scan interval {}".format(self._device.name, self.scan_interval))
        await self._hass.data[DATA_BUSPRO].entity_initialized(self)



    @callback
    def async_register_callbacks(self):
        """Register callbacks to update hass after device was changed."""

        # noinspection PyUnusedLocal
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
    def is_on(self):
        """Return true if light is on."""
        return self._device.is_on

    @property
    def scan_interval(self):
        """Return the scan interval of the switch."""
        return self._scan_interval

    async def async_turn_on(self, **kwargs):
        """Instruct the switch to turn on."""
        await self._device.set_on()

    async def async_turn_off(self, **kwargs):
        """Instruct the switch to turn off."""
        await self._device.set_off()

    @property
    def unique_id(self):
        """Return unique ID for this switch."""
        subnet, device = self._device._device_address
        channel = getattr(self._device, "_channel_number", "N")
        return f"{subnet}-{device}-{channel}-switch"
