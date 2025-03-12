"""Support for HDL Buspro covers."""
import logging
import re
import voluptuous as vol

from homeassistant.components.cover import (
    PLATFORM_SCHEMA,
    CoverEntity,
)
from homeassistant.const import (
    CONF_NAME,
    CONF_ADDRESS,
    CONF_DEVICES,    
)
from homeassistant.components.cover import CoverEntity, CoverEntityFeature, CoverDeviceClass
import homeassistant.helpers.config_validation as cv

from custom_components.buspro.const import CONF_INVERT, DATA_BUSPRO
from custom_components.buspro.helpers import wait_for_buspro
from .pybuspro.devices.cover import Cover

_LOGGER = logging.getLogger(__name__)

def validate_address(value: str) -> str:
    """Validate Buspro device address.
    
    Expected format: subnet.device.channel where:
    - subnet: 0-255
    - device: 0-255
    - channel: 1-2 (HDL device has 2 channels)
    """
    pattern = r'^\d+\.\d+\.\d+$'
    if not re.match(pattern, value):
        raise vol.Invalid(
            f"Invalid address format: {value}. Expected format: 'subnet.device.channel'"
        )
    parts = [int(x) for x in value.split(".")]
    if not (0 <= parts[0] <= 255 and 0 <= parts[1] <= 255 and 1 <= parts[2] <= 2):
        raise vol.Invalid(
            f"Invalid address values: {value}. Subnet and device must be 0-255, channel must be 1-2"
        )
    return value

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_DEVICES): vol.All(cv.ensure_list, [
        vol.Schema({
            vol.Required(CONF_ADDRESS): validate_address,
            vol.Required(CONF_NAME): cv.string,
            vol.Optional(CONF_INVERT, default=False): cv.boolean,
        })
    ])
})

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the HDL Buspro cover devices."""
    devices = []

    if not await wait_for_buspro(hass):
        return False

    devices = []

    for device_config in config[CONF_DEVICES]:
        match = re.match(r'^(\d+)\.(\d+)\.(\d+)$', device_config[CONF_ADDRESS])
        if not match:
            continue
            
        name = device_config[CONF_NAME]
        invert = device_config[CONF_INVERT]
        subnet_id, device_id, channel = map(int, match.groups())
        
        device = Cover(hass, (subnet_id, device_id), channel)
        
        devices.append(HDLBusproCover(
            hass,
            device,
            name,
            invert
        ))
        if _LOGGER.isEnabledFor(logging.DEBUG):
            _LOGGER.debug(f"Added cover '{name}' (invert={invert})")

    async_add_entities(devices)
    return True
    

class HDLBusproCover(CoverEntity):
    """Representation of HDL Buspro Cover."""

    def __init__(self, hass, device,name, invert=False,scan_interval=0):
        """Initialize cover entity.
        
        Args:
            device: Cover device instance
            name: Display name
            address: Device address (subnet.device.channel)
            invert: Invert position values (0=open, 100=closed)
        """
        self._name = name
        self._hass = hass
        self._device = device
        self._invert = invert
        self.scan_interval = scan_interval
        self._device.register_device_updated_cb(self.schedule_update_ha_state)

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        if _LOGGER.isEnabledFor(logging.DEBUG):
            _LOGGER.debug("Added cover '{}' scan interval {}".format(self._device.name, self.scan_interval))
        await self._hass.data[DATA_BUSPRO].entity_initialized(self)

    @property
    def name(self):
        """Return the display name of this cover."""
        return self._name

    @property
    def is_closed(self):                
        return None
        

    @property
    def supported_features(self):
        """Flag supported features."""
        return (
            CoverEntityFeature.OPEN | 
            CoverEntityFeature.CLOSE | 
            CoverEntityFeature.STOP |
            CoverEntityFeature.OPEN_TILT |
            CoverEntityFeature.CLOSE_TILT |
            CoverEntityFeature.STOP_TILT
        )

    @property
    def current_cover_position(self):
        """Return current position of cover."""
        return None
        

    async def async_open_cover(self, **kwargs):
        """Open the cover."""
        if self._invert:
            await self._device.close_cover()
        else:
            await self._device.open_cover()

    async def async_close_cover(self, **kwargs):
        """Close the cover."""
        if self._invert:
            await self._device.open_cover()
        else:
            await self._device.close_cover()

    async def async_stop_cover(self, **kwargs):
        """Stop the cover movement."""
        await self._device.stop()

    async def async_open_cover_tilt(self, **kwargs):
        """Tilt the cover open (small step up)."""
        if self._invert:
            await self._device.small_step_close()
        else:
            await self._device.small_step_open()

    async def async_close_cover_tilt(self, **kwargs):
        """Tilt the cover closed (small step down)."""
        if self._invert:
            await self._device.small_step_open()
        else:
            await self._device.small_step_close()
        
    async def async_stop_cover_tilt(self, **kwargs):
        """Stop the cover tilt movement."""
        await self._device.small_step_stop()
        
    @property
    def should_poll(self):
        """No polling needed within Buspro unless explicitly set."""
        return False
    
#    async def async_update(self):
#        """Update cover state."""        
#        await self._device.read_cover_status()

    @property
    def unique_id(self):
        """Return unique ID for this cover."""
        subnet, device = self._device._device_address
        channel = getattr(self._device, "_channel", "N")
        return f"{subnet}-{device}-{channel}-cover"
