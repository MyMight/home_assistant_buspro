import asyncio
import logging
import struct
from enum import Enum

class SensorType(Enum):
    TEMPERATURE = "temperature"
    ILLUMINANCE = "illuminance"
    HUMIDITY = "humidity"
    MOTION = "motion"
    SONIC = "sonic"
    DRY_CONTACT = "dry_contact"
    DRY_CONTACT_1 = "dry_contact_1"
    DRY_CONTACT_2 = "dry_contact_2"
    UNIVERSAL_SWITCH = "universal_switch"
    SINGLE_CHANNEL = "single_channel"

from .control import _Read12in1SensorStatus, _ReadStatusOfUniversalSwitch, _ReadStatusOfChannels, _ReadFloorHeatingStatus, \
    _ReadDryContactStatus, _ReadSensorsInOneStatus, _ReadTemperatureStatus
from .device import Device
from ..helpers.enums import *

_LOGGER = logging.getLogger(__name__)

class Sensor(Device):
    def __init__(self, hass, device_address, device_family=None, sensor_type=None, universal_switch_number=None, channel_number=None, device=None,
                 switch_number=None, name="", delay_read_current_state_seconds=0):
        super().__init__(hass, device_address, name)

        self._hass = hass
        self._device_address = device_address
        self._sensor_type = SensorType(sensor_type) if sensor_type is not None else None
        self._device_family = DeviceFamily(device_family) if device_family is not None else None
        self._universal_switch_number = universal_switch_number
        self._channel_number = channel_number
        self._name = name
        self._switch_number = switch_number

        self._current_temperature = None
        self._current_humidity = None
        self._brightness = None
        self._motion_sensor = None
        self._sonic = None
        self._dry_contact_1_status = None
        self._dry_contact_2_status = None
        self._universal_switch_status = OnOffStatus.OFF
        self._channel_status = 0
        self._switch_status = 0

        self.register_telegram_received_cb(self._telegram_received_cb)
        self._call_read_current_status_of_sensor(run_from_init=True)

    def _telegram_received_cb(self, telegram):
        if telegram.operate_code in [OperateCode.Read12in1SensorStatusResponse,OperateCode.Broadcast12in1SensorStatusAutoResponse]:
            success_or_fail = telegram.payload[0]
            if success_or_fail == SuccessOrFailure.Success:
                self._current_temperature = telegram.payload[1] - 20
                self._brightness =  (telegram.payload[2] * 256) + telegram.payload[3]            
                self._motion_sensor = telegram.payload[4]
                self._sonic = telegram.payload[5]
                self._dry_contact_1_status = telegram.payload[6]
                self._dry_contact_2_status = telegram.payload[7]
                if _LOGGER.isEnabledFor(logging.DEBUG):
                    _LOGGER.debug(f"12in1 sensor data received - temp:{self._current_temperature}, brightness:{self._brightness}, motion:{self._motion_sensor}, sonic:{self._sonic}, dc1:{self._dry_contact_1_status}, dc2:{self._dry_contact_2_status}")
                self._call_device_updated()
            else:
                _LOGGER.error(f"12in1 sensor data failed to receive - {telegram.payload}")
            if _LOGGER.isEnabledFor(logging.DEBUG):
                msg_type = "broadcast" if telegram.operate_code == OperateCode.Broadcast12in1SensorStatusAutoResponse else "data"
                _LOGGER.debug(f"12in1 sensor {msg_type} received - temp:{self._current_temperature}, brightness:{self._brightness}, motion:{self._motion_sensor}, sonic:{self._sonic}, dc1:{self._dry_contact_1_status}, dc2:{self._dry_contact_2_status}")

        # elif telegram.operate_code == OperateCode.Broadcast12in1SensorStatusAutoResponse:
        #     self._current_temperature = telegram.payload[0] - 20
        #     brightness_high = telegram.payload[1]
        #     brightness_low = telegram.payload[2]
        #     self._motion_sensor = telegram.payload[3]
        #     self._sonic = telegram.payload[4]
        #     self._dry_contact_1_status = telegram.payload[5]
        #     self._dry_contact_2_status = telegram.payload[6]
        #     self._brightness = brightness_high + brightness_low
        #     _LOGGER.debug(f"12in1 broadcast data received - temp:{self._current_temperature}, brightness:{self._brightness}, motion:{self._motion_sensor}, sonic:{self._sonic}, dc1:{self._dry_contact_1_status}, dc2:{self._dry_contact_2_status}")       
        #     self._call_device_updated()

        elif telegram.operate_code in [OperateCode.ReadSensorsInOneStatusResponse,OperateCode.BroadcastSensorsInOneStatusResponse]:
            self._current_temperature = telegram.payload[1] - 20
            self._brightness = (telegram.payload[2] * 256) + telegram.payload[3]
            self._current_humidity = telegram.payload[4]
            self._motion_sensor = telegram.payload[7]
            self._dry_contact_1_status = telegram.payload[8]
            self._dry_contact_2_status = telegram.payload[9]
            if _LOGGER.isEnabledFor(logging.DEBUG):
                msg_type = "broadcast" if telegram.operate_code == OperateCode.BroadcastSensorsInOneStatusResponse else "data"
                _LOGGER.debug(f"Sensors-in-one {msg_type} received - temp:{self._current_temperature}, brightness:{self._brightness}, humidity:{self._current_humidity}, motion:{self._motion_sensor}, dc1:{self._dry_contact_1_status}, dc2:{self._dry_contact_2_status}")        
            self._call_device_updated()

        elif telegram.operate_code == OperateCode.ReadFloorHeatingStatusResponse:
            self._current_temperature = telegram.payload[1]
            if _LOGGER.isEnabledFor(logging.DEBUG):
                _LOGGER.debug(f"Floor heating temperature received - temp:{self._current_temperature}")        
            self._call_device_updated()

        elif telegram.operate_code in [OperateCode.BroadcastTemperatureResponse, OperateCode.ReadTemperatureStatusResponse]:
            if self._channel_number is not None and self._channel_number == telegram.payload[0]:
                self._current_temperature = telegram.payload[1]
                
                if len(telegram.payload) >= 6:
                    if not all(b == 0 for b in telegram.payload[2:6]):
                        try:
                            float_bytes = bytes(telegram.payload[2:6])
                            float_temp = struct.unpack("<f", float_bytes)[0]
                            
                            if -100 < float_temp < 100:
                                self._current_temperature = float_temp                                

                        except (struct.error, ValueError, IndexError) as e:
                            pass
                
                if _LOGGER.isEnabledFor(logging.DEBUG):
                    msg_type = "broadcast" if telegram.operate_code == OperateCode.BroadcastTemperatureResponse else "data"
                    _LOGGER.debug(f"Temperature {msg_type} received - temp: {self._current_temperature}")
                self._call_device_updated()

        elif telegram.operate_code == OperateCode.ReadStatusOfUniversalSwitchResponse:
            switch_number = telegram.payload[0]
            universal_switch_status = telegram.payload[1]

            if switch_number == self._universal_switch_number:
                self._universal_switch_status = universal_switch_status
                if _LOGGER.isEnabledFor(logging.DEBUG):
                    _LOGGER.debug(f"Universal switch status received for switch {switch_number} - status:{self._universal_switch_status}")            
                self._call_device_updated()

        elif telegram.operate_code == OperateCode.BroadcastStatusOfUniversalSwitch:
            if self._universal_switch_number is not None and self._universal_switch_number <= telegram.payload[0]:
                self._universal_switch_status = telegram.payload[self._universal_switch_number]                
                if _LOGGER.isEnabledFor(logging.DEBUG):
                    _LOGGER.debug(f"Universal switch broadcast received for switch {self._universal_switch_number} - status:{self._universal_switch_status}")
                self._call_device_updated()

        elif telegram.operate_code == OperateCode.UniversalSwitchControlResponse:
            switch_number = telegram.payload[0]
            universal_switch_status = telegram.payload[1]

            if switch_number == self._universal_switch_number:
                self._universal_switch_status = universal_switch_status
                if _LOGGER.isEnabledFor(logging.DEBUG):
                    _LOGGER.debug(f"Channel status received for channel {self._channel_number} - status:{self._channel_status}")            
                self._call_device_updated()

        elif telegram.operate_code in [OperateCode.ReadDryContactStatusResponse, OperateCode.ReadDryContactBroadcastStatusResponse]:
            if self._switch_number == telegram.payload[1]:
                self._switch_status = telegram.payload[2]
                if _LOGGER.isEnabledFor(logging.DEBUG):
                    msg_type = "broadcast" if telegram.operate_code == OperateCode.ReadDryContactBroadcastStatusResponse else "data"
                    _LOGGER.debug(f"Dry contact {msg_type} received for switch {self._switch_number} - status:{self._switch_status}")            
                self._call_device_updated()            


    async def read_sensor_status(self):
        if self._device_family is not None and self._device_family == DeviceFamily.DLP:
            if _LOGGER.isEnabledFor(logging.DEBUG):
                _LOGGER.debug(f"Reading DLP floor heating status for device {self._device_address}")
            rfhs = _ReadFloorHeatingStatus(self._hass, self._device_address)            
            await rfhs.send()
        elif self._device_family is not None and self._device_family == DeviceFamily.SENSORS_IN_ONE:
            if _LOGGER.isEnabledFor(logging.DEBUG):
                _LOGGER.debug(f"Reading sensors-in-one status for device {self._device_address}")
            rsios = _ReadSensorsInOneStatus(self._hass, self._device_address)            
            await rsios.send()
        elif self._device_family is not None and self._device_family == DeviceFamily.TWELVE_IN_ONE:
            if _LOGGER.isEnabledFor(logging.DEBUG):
                _LOGGER.debug(f"Reading 12-in-1 sensor status for device {self._device_address}")
            rsios = _Read12in1SensorStatus(self._hass, self._device_address)
            await rsios.send()            
        elif self._sensor_type is not None and self._sensor_type == SensorType.DRY_CONTACT:
            if _LOGGER.isEnabledFor(logging.DEBUG):
                _LOGGER.debug(f"Reading dry contact status for device {self._device_address}, switch {self._switch_number}")
            rdcs = _ReadDryContactStatus(self._hass, self._device_address)            
            rdcs.switch_number = self._switch_number
            await rdcs.send()
        elif self._universal_switch_number is not None:
            if _LOGGER.isEnabledFor(logging.DEBUG):
                _LOGGER.debug(f"Reading universal switch status for device {self._device_address}, switch {self._universal_switch_number}")
            rsous = _ReadStatusOfUniversalSwitch(self._hass, self._device_address)            
            rsous.switch_number = self._universal_switch_number
            await rsous.send()
        elif self._sensor_type is not None and self._sensor_type == SensorType.TEMPERATURE:
            channel = self._channel_number if self._channel_number is not None else 1
            if _LOGGER.isEnabledFor(logging.DEBUG):
                _LOGGER.debug(f"Reading temperature status for device {self._device_address}, channel {channel}")
            rts = _ReadTemperatureStatus(self._hass, self._device_address)            
            rts.channel_number = channel
            await rts.send()
        elif self._sensor_type is not None and self._channel_number is not None:
            if _LOGGER.isEnabledFor(logging.DEBUG):
                _LOGGER.debug(f"Reading channel status for device {self._device_address}")
            rsoc = _ReadStatusOfChannels(self._hass, self._device_address)            
            await rsoc.send()


    @property
    def temperature(self):
        return self._current_temperature


    @property
    def humidity(self):
        return self._current_humidity

    @property
    def brightness(self):
        if self._brightness is None:
            return 0
        return self._brightness

    @property
    def movement(self):
        if self._sensor_type is None:
            return None
        if self._sensor_type == SensorType.SONIC:
            return self._sonic
        return self._motion_sensor        

    @property
    def dry_contact_1_is_on(self):
        if self._dry_contact_1_status == 1:
            return True
        else:
            return False

    @property
    def dry_contact_2_is_on(self):
        if self._dry_contact_2_status == 1:
            return True
        else:
            return False

    @property
    def universal_switch_is_on(self):
        if self._universal_switch_status == 1:
            return True
        else:
            return False

    @property
    def single_channel_is_on(self):
        if self._channel_status > 0:
            return True
        else:
            return False

    @property
    def switch_status(self):
        if self._switch_status == 1:
            return True
        else:
            return False


    def _call_read_current_status_of_sensor(self, run_from_init=False):

        async def read_current_status_of_sensor():
            if run_from_init:
                await asyncio.sleep(5)
            await self.read_sensor_status()

        asyncio.ensure_future(read_current_status_of_sensor(), loop=self._hass.loop)
