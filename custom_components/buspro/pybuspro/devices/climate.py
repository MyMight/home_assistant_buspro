import asyncio
from enum import Enum
import logging

from .control import _FHMControlFloorHeatingStatus, _FHMReadFloorHeatingStatus, _ReadFloorHeatingStatus
from .device import Device
from ..helpers.enums import OperationMode, WorkType, OperateCode, SuccessOrFailure, TemperatureType, TemperatureMode
from ..helpers.generics import Generics

_LOGGER = logging.getLogger(__name__)

class ClimateDeviceType(Enum):
    """HDL Buspro climate device type."""
    PANEL = "panel"
    FLOOR_HEATING = "floor_heating"
    DLP = "dlp"
    AIR_CONDITIONING = "air_conditioning"

class Climate(Device):
    """Representation of HDL Buspro climate device."""

    def __init__(self, hass, device_address, name="", device_type=ClimateDeviceType.PANEL, channel_number=None):
        """Initialize climate device."""
        super().__init__(hass, device_address, name)
        self._device_type = device_type
        self._channel_number = channel_number
        self._temperature = None
        self._target_temperature = None
        self._is_on = None
        self._mode = None
        self._work_type = WorkType

        self._device_address = device_address
        self._hass = hass

        self._temperature_type = None   # Celsius/Fahrenheit
        self._status = None             # On/Off
        self._mode = None               # 1/2/3/4/5 (Normal/Day/Night/Away/Timer)
        self._current_temperature = None
        self._normal_temperature = None
        self._day_temperature = None
        self._night_temperature = None
        self._away_temperature = None
        self._valve_status = None
        self._pwd_value = 0
        self._timer_enabled = None
        self._watering_time = 0

        self.register_telegram_received_cb(self._telegram_received_cb)
        self._hass.loop.create_task(self.read_status())

    def _telegram_received_cb(self, telegram):
        if telegram.operate_code == OperateCode.DLPReadFloorHeatingStatusResponse:
            self._temperature_type = telegram.payload[0]
            self._current_temperature = telegram.payload[1]
            self._status = telegram.payload[2]
            self._mode = telegram.payload[3]
            self._normal_temperature = telegram.payload[4]
            self._day_temperature = telegram.payload[5]
            self._night_temperature = telegram.payload[6]
            self._away_temperature = telegram.payload[7]
            self._call_device_updated()

        elif telegram.operate_code == OperateCode.DLPControlFloorHeatingStatusResponse:
            success_or_fail = telegram.payload[0]
            self._temperature_type = telegram.payload[1]
            self._status = telegram.payload[2]
            self._mode = telegram.payload[3]
            self._normal_temperature = telegram.payload[4]
            self._day_temperature = telegram.payload[5]
            self._night_temperature = telegram.payload[6]
            self._away_temperature = telegram.payload[7]
            self._call_device_updated()

            if success_or_fail == SuccessOrFailure.Success:
                self._call_device_updated()

        elif telegram.operate_code == OperateCode.FHMResponseReadFloorHeatingStatus:
            if self._channel_number is not None and self._channel_number == telegram.payload[0]:
                self._status = telegram.payload[1] & 0x0F
                
                work_type_value = (telegram.payload[1] & 0xF0) >> 4
                try:
                    self._work_type = WorkType(work_type_value)                     
                except ValueError:
                    self._work_type = "unknown"
                    _LOGGER.warning(f"Unknown work type value: {work_type_value}")
                
                if _LOGGER.isEnabledFor(logging.DEBUG):
                    _LOGGER.debug(f"Work type: {self._work_type} (raw: 0x{telegram.payload[1]:02x}, value: {work_type_value}), status: {self._status}")
                
                self._temperature_type = telegram.payload[2]
                temp_byte = telegram.payload[9]
                sign = -1 if (temp_byte & 0x80) else 1
                temp_val = temp_byte & 0x7F
                self._current_temperature = sign * temp_val
                
                self._mode = telegram.payload[3]
                self._normal_temperature = telegram.payload[4]
                self._day_temperature = telegram.payload[5]
                self._night_temperature = telegram.payload[6]
                self._away_temperature = telegram.payload[7]
                self._valve_status = telegram.payload[10] & 0x01

                
                _LOGGER.debug(f"Received status for device {self._device_address} channel {self._channel_number}: "
                              f"current temperature {self._current_temperature} (raw byte 0x{temp_byte:02x}), status {self._status}  mode {self._mode}, working type {self._work_type}, "
                              f"normal temperature {self._normal_temperature}, day temperature {self._day_temperature}, "
                              f"night temperature {self._night_temperature}, away temperature {self._away_temperature} valve status {self._valve_status}")
                self._call_device_updated()

        # elif telegram.operate_code == OperateCode.BroadcastTemperatureResponse:
        #     if self._channel_number is not None and self._channel_number == telegram.payload[0]:
        #         self._current_temperature = telegram.payload[1]
        #         if _LOGGER.isEnabledFor(logging.DEBUG):
        #             _LOGGER.debug(f"Received current temperature for device {self._device_address} channel {self._channel_number}: {self._current_temperature} from broadcast")
        #         self._call_device_updated(should_reschedule=False)  # Don't reset scheduler for broadcast updates
        #         _LOGGER.debug(f"Broadcast temperature response processed for device {self._device_address} channel {self._channel_number}")

    async def _controlFHM(self) -> None:
        if self._device_type == ClimateDeviceType.FLOOR_HEATING:
            control = _FHMControlFloorHeatingStatus(self._hass, self._device_address)
            control.work_type = self._work_type
            control.channel_number = self._channel_number
            control.temperature_type = self._temperature_type
            control.mode = self._mode
            control.normal_temperature = self._normal_temperature
            control.day_temperature = self._day_temperature
            control.night_temperature = self._night_temperature
            control.away_temperature = self._away_temperature
            control.status = self._status
            if _LOGGER.isEnabledFor(logging.DEBUG):
                _LOGGER.debug(f"Sending control message for device {self._device_address} channel {self._channel_number}: work type {self._work_type}, "
                          f"mode {self._mode}, normal temperature {self._normal_temperature}, day temperature {self._day_temperature}, "
                          f"night temperature {self._night_temperature}, away temperature {self._away_temperature}")
            await control.send()


    @property
    def unit_of_measurement(self):
        generics = Generics()
        return generics.get_enum_value(TemperatureType, self._temperature_type)

    @property
    def is_on(self):
        if self._status == 1:
            return True
        else:
            return False

    @property
    def mode(self) -> OperationMode:
        """Return current operation mode."""
        try:
            return OperationMode(self._mode)
        except ValueError:
            _LOGGER.warning(f"Unknown operation mode: {self._mode}, using NORMAL")
            return OperationMode.NORMAL

    async def set_mode(self, mode: OperationMode) -> None:
        """Set operation mode.
        
        Args:
            mode: OperationMode enum value
        """
        if not isinstance(mode, OperationMode):
            _LOGGER.error(f"Invalid mode type: {type(mode)}, expected OperationMode")
            return
            
        self._mode = mode.value
        await self._controlFHM()

    @property
    def target_temperature(self) -> int:
        """Return the target temperature based on current mode."""
        if self._mode == OperationMode.TIMER.value:
            return None
        elif self._mode == OperationMode.NORMAL.value:
            return self._normal_temperature
        elif self._mode == OperationMode.DAY.value:
            return self._day_temperature
        elif self._mode == OperationMode.NIGHT.value:
            return self._night_temperature
        elif self._mode == OperationMode.AWAY.value:
            return self._away_temperature
        return self._normal_temperature

    async def set_temperature(self, temperature: int) -> None:
        """Set temperature for current mode."""
        if not isinstance(temperature, int):
            temperature = round(temperature)
        
        if self._mode == OperationMode.TIMER.value:
            _LOGGER.warning("Cannot set temperature in Timer mode")
            return
        
        if _LOGGER.isEnabledFor(logging.DEBUG):
            _LOGGER.debug(f"Setting temperature {temperature} for mode {self._mode}")
        
        if self._mode == OperationMode.NORMAL.value:
            self._normal_temperature = temperature
        elif self._mode == OperationMode.DAY.value:
            self._day_temperature = temperature
        elif self._mode == OperationMode.NIGHT.value:
            self._night_temperature = temperature
        elif self._mode == OperationMode.AWAY.value:
            self._away_temperature = temperature
        else:
            self._normal_temperature = temperature
            
        await self._controlFHM()

    @property
    def device_type(self):
        """Return device type."""
        return self._device_type
        
    @property
    def normal_temperature(self):
        """Return normal mode temperature."""
        return self._normal_temperature
        
    @property
    def day_temperature(self):
        """Return day mode temperature."""
        return self._day_temperature
        
    @property
    def night_temperature(self):
        """Return night mode temperature."""
        return self._night_temperature
        
    @property
    def away_temperature(self):
        """Return away mode temperature."""
        return self._away_temperature
        
    @property
    def is_power_mode(self) -> bool:
        """Indicates if device is in power mode."""
        if not hasattr(self, '_work_type'):
            return False
        return self._work_type in [WorkType.HEATING_POWER, WorkType.COOLING_POWER]

    async def read_status(self):
        """Read status from the device."""
        if self._device_type == ClimateDeviceType.FLOOR_HEATING:
            fhmrfhs = _FHMReadFloorHeatingStatus(self._hass, self._device_address) 
            fhmrfhs.channel_number = self._channel_number     
            await fhmrfhs.send()                
        elif self._device_type == ClimateDeviceType.DLP:
            rfhs = _ReadFloorHeatingStatus(self._hass, self._device_address) 
            await rfhs.send()

    async def set_work_type(self, work_type: WorkType) -> None:
        """Set work type for floor heating."""
        self._work_type = work_type
        self._status = 1
        await self._controlFHM()

    async def turn_on(self) -> None:
        """Turn the device on."""
        self._status = 1
        await self._controlFHM()

    async def turn_off(self) -> None:
        """Turn the device off."""
        self._status = 0
        await self._controlFHM()

