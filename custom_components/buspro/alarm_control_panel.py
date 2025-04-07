"""Support for HDL Buspro alarm control panel."""
import logging
import re
import voluptuous as vol

from homeassistant.components.alarm_control_panel import (
    PLATFORM_SCHEMA,
    AlarmControlPanelEntity,
    AlarmControlPanelEntityFeature,
)
from homeassistant.components.alarm_control_panel.const import (
    AlarmControlPanelState,
)
from homeassistant.const import (
    CONF_NAME,
    CONF_ADDRESS,
    CONF_DEVICES,
    CONF_SCAN_INTERVAL,
)
import homeassistant.helpers.config_validation as cv
from homeassistant.core import callback
from homeassistant.helpers.restore_state import RestoreEntity
from custom_components.buspro.const import DATA_BUSPRO
from custom_components.buspro.helpers import wait_for_buspro
from .pybuspro.devices.security import Security, SecurityStatus

_LOGGER = logging.getLogger(__name__)

# Mapping between Home Assistant states (key) and HDL Buspro SecurityStatus (value)
STATE_MAP = {
    AlarmControlPanelState.DISARMED: SecurityStatus.DISARM,
    AlarmControlPanelState.ARMED_HOME: SecurityStatus.DAY,
    AlarmControlPanelState.ARMED_NIGHT: SecurityStatus.NIGHT,
    AlarmControlPanelState.ARMED_AWAY: SecurityStatus.AWAY,
    AlarmControlPanelState.ARMED_VACATION: SecurityStatus.VACATION,
    AlarmControlPanelState.ARMED_CUSTOM_BYPASS: SecurityStatus.NIGHT_WITH_GUEST,
}

# Create inverse mapping by swapping keys and values
INVERSE_STATE_MAP = {v: k for k, v in STATE_MAP.items()}


def validate_address(value: str) -> str:
    """Validate Buspro device address.
    
    Expected format: subnet.device.area where:
    - subnet: 0-255
    - device: 0-255
    - area: 1-8
    """
    pattern = r'^\d+\.\d+\.\d+$'
    if not re.match(pattern, value):
        raise vol.Invalid(
            f"Invalid address format: {value}. Expected format: 'subnet.device.area'"
        )
    parts = [int(x) for x in value.split(".")]
    if not (0 <= parts[0] <= 255 and 0 <= parts[1] <= 255):
        raise vol.Invalid(
            f"Invalid address values: {value}. Subnet and device must be 0-255"
        )
    if not (1 <= parts[2] <= 8):
        raise vol.Invalid(
            f"Invalid area value: {parts[2]}. Area must be 1-8"
        )
    return value

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_DEVICES): vol.All(cv.ensure_list, [
        vol.Schema({
            vol.Required(CONF_ADDRESS): validate_address,
            vol.Required(CONF_NAME): cv.string,
            vol.Optional(CONF_SCAN_INTERVAL, default=0): cv.positive_int,            
        })
    ])
})

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the HDL Buspro alarm control panel devices."""
    if not await wait_for_buspro(hass):
        return False
    
    devices = []

    for device_config in config[CONF_DEVICES]:
        match = re.match(r'^(\d+)\.(\d+)\.(\d+)$', device_config[CONF_ADDRESS])
        if not match:
            continue
            
        name = device_config[CONF_NAME]
        scan_interval = device_config.get(CONF_SCAN_INTERVAL, 0)        
        subnet_id, device_id, area_id = map(int, match.groups())
        
        device = Security(hass, (subnet_id, device_id), area_id, name)
        panel = HDLBusproAlarmPanel(hass, device, name, scan_interval)
        devices.append(panel)

    async_add_entities(devices)
    return True

class HDLBusproAlarmPanel(AlarmControlPanelEntity, RestoreEntity):
    """Representation of HDL Buspro Alarm Control Panel."""
    
    def __init__(self, hass, device, name, scan_interval=0):
        """Initialize alarm control panel entity."""
        self._name = name
        self._hass = hass
        self._device = device
        self._scan_interval = scan_interval        
        self._attr_supported_features = (
            AlarmControlPanelEntityFeature.ARM_HOME |
            AlarmControlPanelEntityFeature.ARM_AWAY |
            AlarmControlPanelEntityFeature.ARM_NIGHT |
            AlarmControlPanelEntityFeature.ARM_VACATION |
            AlarmControlPanelEntityFeature.ARM_CUSTOM_BYPASS |
            AlarmControlPanelEntityFeature.TRIGGER
        )
        
        self._attr_code_format = None
        self._attr_code_arm_required = False
        self.async_register_callbacks()

    async def async_added_to_hass(self):
        """When entity is added to hass."""
        await super().async_added_to_hass()
        
        last_state = await self.async_get_last_state()
        if last_state is not None and last_state.state in STATE_MAP:
            self._device._status = STATE_MAP[last_state.state]
        
        await self._hass.data[DATA_BUSPRO].entity_initialized(self)
        await self.async_update()
    


    @callback
    def async_register_callbacks(self):
        """Register callbacks to update hass after device was changed."""

        async def after_update_callback(device, should_reschedule=True):
            """Call after device was updated."""
            self.async_write_ha_state()
            await self._hass.data[DATA_BUSPRO].scheduler.device_updated(self.entity_id)
        
        self._device.register_device_updated_cb(after_update_callback)    

    @property
    def name(self):
        """Return the display name of this alarm panel."""
        return self._name

    @property
    def alarm_state(self) -> AlarmControlPanelState:
        """Return the state of the alarm panel using AlarmControlPanelState enum."""
        if self._device.status is None:
            return None
            
        return INVERSE_STATE_MAP.get(self._device.status, None)

    async def async_alarm_disarm(self, code=None):
        """Send disarm command."""
        if _LOGGER.isEnabledFor(logging.DEBUG):
            _LOGGER.debug(f"Disarming alarm panel '{self._name}', sending DISARM command")
        await self._device.set_status(SecurityStatus.DISARM)

    async def async_alarm_arm_home(self, code=None):
        """Send arm home command."""
        if _LOGGER.isEnabledFor(logging.DEBUG):
            _LOGGER.debug(f"Arming alarm panel '{self._name}' to HOME mode, sending DAY command")
        await self._device.set_status(SecurityStatus.DAY)

    async def async_alarm_arm_away(self, code=None):
        """Send arm away command."""
        if _LOGGER.isEnabledFor(logging.DEBUG):
            _LOGGER.debug(f"Arming alarm panel '{self._name}' to AWAY mode, sending AWAY command")
        await self._device.set_status(SecurityStatus.AWAY)        

    async def async_alarm_arm_night(self, code=None):
        """Send arm night command."""
        if _LOGGER.isEnabledFor(logging.DEBUG):
            _LOGGER.debug(f"Arming alarm panel '{self._name}' to NIGHT mode, sending NIGHT command")
        await self._device.set_status(SecurityStatus.NIGHT)

    async def async_alarm_arm_vacation(self, code=None):
        """Send arm vacation command."""
        if _LOGGER.isEnabledFor(logging.DEBUG):
            _LOGGER.debug(f"Arming alarm panel '{self._name}' to VACATION mode, sending VACATION command")
        await self._device.set_status(SecurityStatus.VACATION)

    async def async_alarm_arm_custom_bypass(self, code=None):
        """Send arm custom bypass command."""
        if _LOGGER.isEnabledFor(logging.DEBUG):
            _LOGGER.debug(f"Arming alarm panel '{self._name}' to CUSTOM BYPASS mode, sending NIGHT_WITH_GUEST command")
        await self._device.set_status(SecurityStatus.NIGHT_WITH_GUEST)

    async def async_alarm_trigger(self, code=None):
        """Send alarm trigger command."""
        if _LOGGER.isEnabledFor(logging.DEBUG):
            _LOGGER.debug(f"Triggering alarm panel '{self._name}', sending AWAY command as trigger")
        await self._device.set_status(SecurityStatus.AWAY)

    async def async_update(self):
        """Update alarm panel state."""
        await self._device.read_security_status()

    @property
    def should_poll(self):
        """Return True if entity has to be polled for state."""
        return False

    @property
    def unique_id(self):
        """Return unique ID for this alarm panel."""
        return f"{self._device._device_address[0]}-{self._device._device_address[1]}-{self._device._area_id}-alarm"

    @property
    def scan_interval(self):
        """Return the scan interval for this entity."""
        return self._scan_interval