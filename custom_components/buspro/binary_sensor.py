"""
This component provides binary sensor support for Buspro.
"""

import asyncio
import logging
import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.components.binary_sensor import (
    PLATFORM_SCHEMA, 
    BinarySensorEntity,
    DEVICE_CLASSES_SCHEMA
)
from homeassistant.const import (
    CONF_NAME, CONF_DEVICES, CONF_ADDRESS, CONF_TYPE, 
    CONF_DEVICE, CONF_SCAN_INTERVAL, CONF_DEVICE_CLASS
)
from homeassistant.core import callback

from custom_components.buspro.helpers import wait_for_buspro
from custom_components.buspro.pybuspro.devices.sensor import SensorType
from .pybuspro.helpers.enums import DeviceFamily, validate_device_family
from .pybuspro.devices.sensor import Sensor, SensorType
from ..buspro import DATA_BUSPRO

_LOGGER = logging.getLogger(__name__)

DEFAULT_CONF_DEVICE = "None"
DEFAULT_CONF_SCAN_INTERVAL = 0

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_DEVICES):
        vol.All(cv.ensure_list, [
            vol.All({
                vol.Required(CONF_ADDRESS): cv.string,
                vol.Required(CONF_NAME): cv.string,
                vol.Required(CONF_TYPE): cv.string,  # Expecting string from config                
                vol.Optional(CONF_DEVICE, default=DEFAULT_CONF_DEVICE): vol.All(cv.string, validate_device_family),
                vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_CONF_SCAN_INTERVAL): cv.positive_int,
                vol.Optional(CONF_DEVICE_CLASS): DEVICE_CLASSES_SCHEMA,
            })
        ])
})


# noinspection PyUnusedLocal
async def async_setup_platform(hass, config, async_add_entites, discovery_info=None):
    """Set up Buspro binary sensor devices."""
    
    if not await wait_for_buspro(hass):
        return False    
    devices = []

    for device_config in config[CONF_DEVICES]:
        address = device_config[CONF_ADDRESS]
        name = device_config[CONF_NAME]
        sensor_type_str = device_config[CONF_TYPE]  # Get sensor type as string
        device_family_str = device_config[CONF_DEVICE]
        device_class = device_config.get(CONF_DEVICE_CLASS)

        # Convert string representations to enums
        try:
            sensor_type = SensorType(sensor_type_str)
        except ValueError:
            _LOGGER.error(f"Invalid sensor type: {sensor_type_str}")
            continue

        try:
            device_family = DeviceFamily(device_family_str) if device_family_str != "None" else None
        except ValueError:
            _LOGGER.error(f"Invalid device class: {device_family_str}")
            continue

        scan_interval = device_config[CONF_SCAN_INTERVAL]

        address2 = address.split('.')
        device_address = (int(address2[0]), int(address2[1]))

        if _LOGGER.isEnabledFor(logging.DEBUG):
            _LOGGER.debug(f"Adding binary sensor '{name}' with address {device_address}, sensor type '{sensor_type}'")

        
        if sensor_type == SensorType.DRY_CONTACT:
            switch_number = int(address2[2]) if len(address2) > 2 else 1
            sensor = Sensor(hass, device_address, device_family=device_family, sensor_type=sensor_type.value, name=name, switch_number=switch_number)
        elif sensor_type == SensorType.SINGLE_CHANNEL:
            channel_number = int(address2[2])
            sensor = Sensor(hass, device_address, device_family=device_family, sensor_type=sensor_type.value, name=name, channel_number=channel_number)
        elif sensor_type == SensorType.UNIVERSAL_SWITCH:
            universal_switch_number = int(address2[2])
            sensor = Sensor(hass, device_address, device_family=device_family, sensor_type=sensor_type.value, name=name, universal_switch_number=universal_switch_number)
        else: 
            sensor = Sensor(hass, device_address, device_family=device_family, sensor_type=sensor_type.value, name=name)

        devices.append(BusproBinarySensor(hass, sensor, sensor_type, scan_interval, device_class))

    async_add_entites(devices)


# noinspection PyAbstractClass
class BusproBinarySensor(BinarySensorEntity):
    """Representation of a Buspro binary sensor."""

    def __init__(self, hass, device, sensor_type, scan_interval, device_class=None):
        """Initialize the Buspro binary sensor."""
        self._hass = hass
        self._device = device
        self._sensor_type = sensor_type
        self._scan_interval = scan_interval
        self._custom_device_class = device_class
        self._is_on = False  # Initial state
        self.async_register_callbacks()

    async def async_added_to_hass(self):
        """Run when entity about to be added to hass."""
        await super().async_added_to_hass()
        if _LOGGER.isEnabledFor(logging.DEBUG):
            _LOGGER.debug(f"Added binary sensor '{self._device.name}' scan interval {self.scan_interval}")
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
    def is_on(self):
        """Return true if the binary sensor is on."""
        if self._sensor_type == SensorType.MOTION:
            return self._device.movement
        elif self._sensor_type == SensorType.DRY_CONTACT_1:
            return self._device.dry_contact_1_is_on
        elif self._sensor_type == SensorType.DRY_CONTACT_2:
            return self._device.dry_contact_2_is_on
        elif self._sensor_type == SensorType.UNIVERSAL_SWITCH:
            return self._device.universal_switch_is_on
        elif self._sensor_type == SensorType.SINGLE_CHANNEL:
            return self._device.single_channel_is_on
        if self._sensor_type == SensorType.DRY_CONTACT:
            return self._device.switch_status        
        return self._device.switch_status

    @property
    def should_poll(self):
        """No polling needed within Buspro unless explicitly set."""
        return False
    
    async def async_update(self):
        await self._device.read_sensor_status()

    @property
    def name(self):
        """Return the name of the binary sensor."""
        return self._device.name

    @property
    def unique_id(self):
        """Return unique ID for this binary sensor."""
        subnet, device = self._device._device_address
        
        if self._sensor_type == SensorType.DRY_CONTACT:
            channel = getattr(self._device, "_switch_number", "N")
        elif self._sensor_type == SensorType.UNIVERSAL_SWITCH:
            channel = getattr(self._device, "_universal_switch_number", "N")
        elif self._sensor_type == SensorType.SINGLE_CHANNEL:
            channel = getattr(self._device, "_channel_number", "N")
        else:
            channel = "N"
        
        return f"{subnet}-{device}-{channel}-binary_sensor-{self._sensor_type.value}"

    @property
    def scan_interval(self):
        """Return the scan interval of the sensor."""
        return self._scan_interval

    @property
    def device_class(self):
        """Return the class of this device."""
        if self._custom_device_class is not None:
            return self._custom_device_class            
        if self._sensor_type == SensorType.MOTION:
            return "motion"
        return None
