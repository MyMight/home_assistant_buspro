"""
This component provides sensor support for Buspro.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/...
"""

import logging
from typing import Optional, List
from enum import Enum

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.components.climate import (
    PLATFORM_SCHEMA,
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
    HVACAction,
)
from homeassistant.components.climate.const import (
    PRESET_NONE,
    PRESET_HOME,
    PRESET_SLEEP,
    PRESET_AWAY,
    PRESET_ECO,
)
from homeassistant.const import (
    CONF_NAME,
    CONF_DEVICES,
    CONF_ADDRESS,
    UnitOfTemperature,
    ATTR_TEMPERATURE, CONF_SCAN_INTERVAL,
)
from homeassistant.core import callback

from custom_components.buspro.helpers import wait_for_buspro
from custom_components.buspro.pybuspro.devices.climate import Climate, ClimateDeviceType, WorkType
from custom_components.buspro.pybuspro.devices.sensor import Sensor

from ..buspro import DATA_BUSPRO
from .pybuspro.helpers.enums import OperationMode

_LOGGER = logging.getLogger(__name__)

# Map between HDL modes and Home Assistant preset modes
HDL_TO_HA_PRESETS = {
    OperationMode.NORMAL: PRESET_NONE,
    OperationMode.DAY: PRESET_HOME,
    OperationMode.NIGHT: PRESET_SLEEP, 
    OperationMode.AWAY: PRESET_AWAY,
    OperationMode.TIMER: PRESET_ECO,
}

# List of preset modes in default order based on HDL modes
DEFAULT_PRESET_MODES = list(HDL_TO_HA_PRESETS.values())

# Reverse mapping for conversion from HA to HDL
HA_TO_HDL_PRESETS = {v: k for k, v in HDL_TO_HA_PRESETS.items()}

# Mapping for HVAC modes
HVAC_MODE_MAPPING = {
    "heat": HVACMode.HEAT,
    "cool": HVACMode.COOL,
}

CONF_PRESET_MODES = "preset_modes"
CONF_RELAY_ADDRESS = "relay_address"
CONF_HVAC_MODES = "hvac_modes"  # Nová konfigurace

# Funkce pro validaci typu klimatického zařízení
def validate_climate_device_type(value):
    """Validate climate device type."""
    try:
        return ClimateDeviceType(value).value
    except ValueError:
        raise vol.Invalid(f"Invalid climate device type '{value}'")

# Konstanty
DEFAULT_CONF_DEVICE = "panel"  # Původní výchozí hodnota
CONF_DEVICE = "device"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_DEVICES):
        vol.All(cv.ensure_list, [
            vol.All({
                vol.Required(CONF_ADDRESS): cv.string,
                vol.Required(CONF_NAME): cv.string,
                vol.Optional(CONF_DEVICE, default=DEFAULT_CONF_DEVICE): 
                    vol.All(cv.string, validate_climate_device_type),
                vol.Optional(CONF_PRESET_MODES, default=[]): vol.All(
                    cv.ensure_list, [vol.In(HA_TO_HDL_PRESETS.keys())]
                ),
                vol.Optional(CONF_HVAC_MODES, default=[]): vol.All(  # Nová validace
                    cv.ensure_list, [vol.In(HVAC_MODE_MAPPING.keys())]
                ),
                vol.Optional(CONF_RELAY_ADDRESS, default=''): cv.string,
                vol.Optional(CONF_SCAN_INTERVAL, default=0): cv.positive_int,
            })
        ])
})


# noinspection PyUnusedLocal
async def async_setup_platform(hass, config, async_add_entites, discovery_info=None):
    """Set up Buspro climate devices."""
    if not await wait_for_buspro(hass):
        return False    
    devices = []

    for device_config in config[CONF_DEVICES]:
        address = device_config[CONF_ADDRESS]
        name = device_config[CONF_NAME]
        device_type_str = device_config[CONF_DEVICE]
        preset_modes = device_config[CONF_PRESET_MODES]

        try:
            device_type = ClimateDeviceType(device_type_str)
        except ValueError:
            _LOGGER.error(f"Invalid device type: {device_type_str}")
            continue

        # Rozdělení adresy na části
        address2 = address.split('.')
        
        # Kontrola formátu adresy podle typu zařízení
        if len(address2) < 2:
            _LOGGER.error(f"Invalid address format for '{name}': {address}. Expected at least subnet.device")
            continue
            
        device_address = (int(address2[0]), int(address2[1]))
        
        # Zpracování čísla kanálu
        channel_number = None
        if len(address2) > 2:
            channel_number = int(address2[2])
        elif device_type != ClimateDeviceType.DLP:
            _LOGGER.error(f"Missing channel number for '{name}' with device type '{device_type.value}'. Expected format: subnet.device.channel")
            continue

        scan_interval = device_config[CONF_SCAN_INTERVAL]

        if _LOGGER.isEnabledFor(logging.DEBUG):
            channel_info = f", channel {channel_number}" if channel_number is not None else ""
            _LOGGER.debug(f"Adding climate '{name}' with address {device_address}{channel_info}, device type '{device_type.value}'")

        climate = Climate(hass, device_address, name, device_type, channel_number)

        relay_sensor = None
        relay_address = device_config[CONF_RELAY_ADDRESS]
        if relay_address:
            relay_address2 = relay_address.split('.')
            if len(relay_address2) < 3:
                _LOGGER.error(f"Invalid relay address format for '{name}': {relay_address}. Expected subnet.device.channel")
                continue
                
            relay_device_address = (int(relay_address2[0]), int(relay_address2[1]))
            relay_channel_number = int(relay_address2[2])
            relay_sensor = Sensor(hass, relay_device_address, channel_number=relay_channel_number)

        hvac_modes = device_config[CONF_HVAC_MODES]  # Přidáno
        devices.append(BusproClimate(hass, climate, preset_modes, relay_sensor, scan_interval, hvac_modes))  # Upraveno

    async_add_entites(devices)


# noinspection PyAbstractClass
class BusproClimate(ClimateEntity):
    """Representation of a Buspro switch."""

    def __init__(self, hass, device, preset_modes, relay_sensor, scan_interval, hvac_modes):  # Upraveno
        self._hass = hass
        self._device = device
        self._scan_interval = scan_interval
        self._target_temperature = self._device.target_temperature
        self._is_on = self._device.is_on
        self._preset_modes = preset_modes
        self._mode = self._device.mode  # 1/3/4

        self._relay_sensor = relay_sensor
        self._relay_sensor_is_on = None
        if self._relay_sensor is not None:
            self._relay_sensor_is_on = self._relay_sensor.single_channel_is_on

        self._enable_turn_on_off_backwards_compatibility = False
        self._attr_supported_features = (
            ClimateEntityFeature.TARGET_TEMPERATURE |
            ClimateEntityFeature.PRESET_MODE |
            ClimateEntityFeature.TURN_OFF |
            ClimateEntityFeature.TURN_ON
        )

        self._hvac_modes = hvac_modes

        self.async_register_callbacks()

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        if _LOGGER.isEnabledFor(logging.DEBUG):
            _LOGGER.debug("Added climate '{}' scan interval {}".format(self._device.name, self.scan_interval))
        await self._hass.data[DATA_BUSPRO].entity_initialized(self)        
        await self.async_update()        
       
        
    @callback
    def async_register_callbacks(self):
        """Register callbacks to update hass after device was changed."""

        async def after_update_callback(device, should_reschedule=True):
            """Call after device was updated."""
            self.async_write_ha_state()
            await self._hass.data[DATA_BUSPRO].scheduler.device_updated(self.entity_id, should_reschedule)
        
        self._device.register_device_updated_cb(after_update_callback)    


    @property
    def should_poll(self):
        """Return False as we use scheduler instead of polling."""
        return False

    async def async_update(self):
        """Update the state of climate device."""
        await self._device.read_status()

    @property 
    def scan_interval(self):
        """Return scan interval."""
        return self._scan_interval

    @property
    def name(self):
        """Return the display name of this light."""
        return self._device.name

    @property
    def temperature_unit(self):
        """Return the unit of measurement."""
        return UnitOfTemperature.CELSIUS

    @property
    def current_temperature(self):
        """Return the current temperature."""
        return self._device._current_temperature

    @property
    def target_temperature(self) -> float | None:
        """Return the temperature we try to reach."""
        return None if self.preset_mode == PRESET_ECO else self._device.target_temperature

    @property
    def preset_mode(self) -> Optional[str]:
        """Return the current preset mode."""
        return HDL_TO_HA_PRESETS.get(self._device.mode, PRESET_NONE)

    @property
    def preset_modes(self) -> Optional[List[str]]:
        """Return a list of available preset modes."""
        if self._preset_modes:
            # Zachová pořadí z konfigurace
            return self._preset_modes
            
        if self._device.device_type == ClimateDeviceType.FLOOR_HEATING:
            return DEFAULT_PRESET_MODES
        
        return DEFAULT_PRESET_MODES[:-1]  # Všechny kromě ECO módu

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set new preset mode."""
        if preset_mode not in HA_TO_HDL_PRESETS:
            preset_mode = PRESET_NONE
        
        operation_mode = HA_TO_HDL_PRESETS[preset_mode]
        await self._device.set_mode(operation_mode)
        self.async_write_ha_state()

    @property
    def hvac_action(self) -> Optional[str]:
        """Return current action ie. heating, idle, off."""
        if not self._is_on:
            return HVACAction.OFF
            
        if self._relay_sensor_is_on is None or self._relay_sensor_is_on:
            return HVACAction.HEATING
            
        return HVACAction.IDLE

    @property
    def hvac_mode(self) -> str:
        """Return hvac operation mode."""
        if not self._device.is_on:
            return HVACMode.OFF
            
        if self._device.device_type == ClimateDeviceType.FLOOR_HEATING:
            work_type = self._device._work_type
            if work_type in (WorkType.HEATING, WorkType.HEATING_POWER):
                return HVACMode.HEAT
            if work_type in (WorkType.COOLING, WorkType.COOLING_POWER):
                return HVACMode.COOL
                
        return HVACMode.HEAT

    @property
    def hvac_modes(self) -> list[str]:
        """Return the list of available hvac operation modes."""
        modes = [HVACMode.OFF]  # Vždy zahrnout OFF mód
        
        # Pokud není konfigurace, vrátit všechny podporované módy
        if not self._hvac_modes:
            if self._device.device_type == ClimateDeviceType.FLOOR_HEATING:
                return [HVACMode.OFF, HVACMode.HEAT, HVACMode.COOL]
            return [HVACMode.OFF, HVACMode.HEAT]
            
        # Jinak vrátit pouze nakonfigurované módy
        for mode in self._hvac_modes:
            modes.append(HVAC_MODE_MAPPING[mode])
            
        return modes

    async def async_set_hvac_mode(self, hvac_mode: str) -> None:
        """Set new target hvac mode."""
        if hvac_mode == HVACMode.OFF:
            await self._device.turn_off()
        else:            
            if hvac_mode == HVACMode.HEAT:
                work_type = WorkType.HEATING if not self._device.is_power_mode else WorkType.HEATING_POWER
            elif hvac_mode == HVACMode.COOL:
                work_type = WorkType.COOLING if not self._device.is_power_mode else WorkType.COOLING_POWER
                    
            await self._device.set_work_type(work_type)

        self.async_write_ha_state()

    @property
    def target_temperature_step(self):
        """Return the supported step of target temperature."""
        return 1  # HDL only supports integer values

    async def async_set_temperature(self, **kwargs: dict) -> None:
        """Set new target temperature."""
        if ATTR_TEMPERATURE not in kwargs:
            _LOGGER.warning("Received temperature update without temperature value")
            return

        if self.preset_mode == PRESET_ECO:
            _LOGGER.warning("Cannot set temperature in Eco mode (Timer)")
            return
            
        try:
            temperature = round(float(kwargs[ATTR_TEMPERATURE]))
            await self._device.set_temperature(temperature)
            self.async_write_ha_state()
        except Exception as e:
            _LOGGER.error(f"Failed to set temperature for {self.name}: {e}")

    @property
    def min_temp(self) -> float:
        """Return the minimum temperature."""
        return 5
    
    @property
    def max_temp(self) -> float:
        """Return the maximum temperature."""
        return 35

    @property
    def unique_id(self):
        """Return unique ID for this climate entity."""
        subnet, device = self._device._device_address
        device_type = self._device.device_type.value if self._device.device_type else "unknown"        
        
        channel_suffix = ""
        if hasattr(self._device, "_channel_number") and self._device._channel_number is not None:
            channel_suffix = f"-{self._device._channel_number}"
            
        return f"{subnet}-{device}{channel_suffix}-{device_type}-climate"

    @property
    def is_on(self) -> bool:
        """Return true if the entity is on."""
        return self._device.is_on

    async def async_turn_off(self) -> None:
        await self._device.turn_off()        
        

    async def async_turn_on(self) -> None:
        await self._device.turn_on()