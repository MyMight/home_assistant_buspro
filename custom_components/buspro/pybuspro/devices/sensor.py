import asyncio
import struct
from enum import Enum

class SensorType(Enum):
    NONE = None
    TEMPERATURE = "temperature"
    ILLUMINANCE = "illuminance"
    HUMIDITY = "humidity"
    MOTION = "motion"
    DRY_CONTACT_1 = "dry_contact_1"
    DRY_CONTACT_2 = "dry_contact_2"
    UNIVERSAL_SWITCH = "universal_switch"
    SINGLE_CHANNEL = "single_channel"


class DeviceClass(Enum):
    NONE = None
    TWELVE_IN_ONE = "12in1"
    DLP = "dlp"
    ITOUCH = "itouch"
    SENSORS_IN_ONE = "sensors_in_one"

from .control import _ReadSensorStatus, _ReadStatusOfUniversalSwitch, _ReadStatusOfChannels, _ReadFloorHeatingStatus, \
    _ReadDryContactStatus, _ReadSensorsInOneStatus, _ReadTemperatureStatus
from .device import Device
from ..helpers.enums import *


class Sensor(Device):
    def __init__(self, buspro, device_address,device_class=None, sensor_type=None, universal_switch_number=None, channel_number=None, device=None,
                 switch_number=None, name="", delay_read_current_state_seconds=0):
        super().__init__(buspro, device_address, name)

        self._buspro = buspro
        self._device_address = device_address
        self._sensor_type = SensorType(sensor_type)
        self._device_class = DeviceClass(device_class)
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
        if telegram.operate_code == OperateCode.ReadSensorStatusResponse:
            success_or_fail = telegram.payload[0]
            self._current_temperature = telegram.payload[1]
            brightness_high = telegram.payload[2]
            brightness_low = telegram.payload[3]
            self._motion_sensor = telegram.payload[4]
            self._sonic = telegram.payload[5]
            self._dry_contact_1_status = telegram.payload[6]
            self._dry_contact_2_status = telegram.payload[7]
            if success_or_fail == SuccessOrFailure.Success:
                self._brightness = brightness_high + brightness_low
                self._call_device_updated()

        elif telegram.operate_code == OperateCode.ReadSensorsInOneStatusResponse:
            self._current_temperature = telegram.payload[1]
            self._brightness = (telegram.payload[2] * 256) + telegram.payload[3]
            self._current_humidity = telegram.payload[4]
            self._motion_sensor = telegram.payload[7]
            self._dry_contact_1_status = telegram.payload[8]
            self._dry_contact_2_status = telegram.payload[9]
            self._call_device_updated()

        elif telegram.operate_code == OperateCode.BroadcastSensorStatusResponse:
            self._current_temperature = telegram.payload[0]
            brightness_high = telegram.payload[1]
            brightness_low = telegram.payload[2]
            self._motion_sensor = telegram.payload[3]
            self._sonic = telegram.payload[4]
            self._dry_contact_1_status = telegram.payload[5]
            self._dry_contact_2_status = telegram.payload[6]
            self._brightness = brightness_high + brightness_low
            self._call_device_updated()

        elif telegram.operate_code == OperateCode.ReadTemperatureStatusResponse:
            if self._channel_number == telegram.payload[0]:
                self._temperature = struct.unpack('>8h', telegram.payload[1])

        elif telegram.operate_code == OperateCode.BroadcastSensorStatusAutoResponse:
            self._current_temperature = telegram.payload[0]
            if self._device_class == DeviceClass.TWELVE_IN_ONE:
                self._current_temperature = self._current_temperature - 20
            
            brightness_high = telegram.payload[1]
            brightness_low = telegram.payload[2]
            self._motion_sensor = telegram.payload[3]
            self._sonic = telegram.payload[4]
            self._dry_contact_1_status = telegram.payload[5]
            self._dry_contact_2_status = telegram.payload[6]
            self._brightness = brightness_high + brightness_low
            self._call_device_updated()

        elif telegram.operate_code == OperateCode.ReadFloorHeatingStatusResponse:
            self._current_temperature = telegram.payload[1]
            self._call_device_updated()

        elif telegram.operate_code == OperateCode.BroadcastTemperatureResponse:
            self._current_temperature = telegram.payload[1]
            self._call_device_updated()

        elif telegram.operate_code == OperateCode.ReadStatusOfUniversalSwitchResponse:
            switch_number = telegram.payload[0]
            universal_switch_status = telegram.payload[1]

            if switch_number == self._universal_switch_number:
                self._universal_switch_status = universal_switch_status
                self._call_device_updated()

        elif telegram.operate_code == OperateCode.BroadcastStatusOfUniversalSwitch:
            if self._universal_switch_number is not None and self._universal_switch_number <= telegram.payload[0]:
                self._universal_switch_status = telegram.payload[self._universal_switch_number]
                self._call_device_updated()

        elif telegram.operate_code == OperateCode.UniversalSwitchControlResponse:
            switch_number = telegram.payload[0]
            universal_switch_status = telegram.payload[1]

            if switch_number == self._universal_switch_number:
                self._universal_switch_status = universal_switch_status
                self._call_device_updated()

        elif telegram.operate_code == OperateCode.ReadStatusOfChannelsResponse:
            if self._channel_number <= telegram.payload[0]:
                self._channel_status = telegram.payload[self._channel_number]
                self._call_device_updated()

        elif telegram.operate_code == OperateCode.SingleChannelControlResponse:
            if self._channel_number == telegram.payload[0]:
                # if telegram.payload[1] == SuccessOrFailure.Success::
                self._channel_status = telegram.payload[2]
                self._call_device_updated()

        elif telegram.operate_code == OperateCode.ReadDryContactStatusResponse:
            if self._switch_number == telegram.payload[1]:
                self._switch_status = telegram.payload[2]
                self._call_device_updated()
        
        if self._current_temperature is not None and self._device_class in [DeviceClass.TWELVE_IN_ONE,DeviceClass.SENSORS_IN_ONE]:
            self._current_temperature = self._current_temperature - 20


    async def read_sensor_status(self):
        if self._universal_switch_number is not None:
            rsous = _ReadStatusOfUniversalSwitch(self._buspro)
            rsous.subnet_id, rsous.device_id = self._device_address
            rsous.switch_number = self._universal_switch_number
            await rsous.send()
        elif self._sensor_type == SensorType.TEMPERATURE and self._channel_number is not None:
            rts = _ReadTemperatureStatus(self._buspro)
            rts.subnet_id, rts.device_id = self._device_address
            rts.channel_number = self._channel_number
            await rts.send()
        elif self._device_class == DeviceClass.ITOUCH:
            rts = _ReadTemperatureStatus(self._buspro)
            rts.subnet_id, rts.device_id = self._device_address
            rts.channel_number = 1
            await rts.send()
        elif self._channel_number is not None:
            rsoc = _ReadStatusOfChannels(self._buspro)
            rsoc.subnet_id, rsoc.device_id = self._device_address
            await rsoc.send()
        elif self._device_class == DeviceClass.DLP:
            rfhs = _ReadFloorHeatingStatus(self._buspro)
            rfhs.subnet_id, rfhs.device_id = self._device_address
            await rfhs.send()
        elif self._sensor_type in [SensorType.DRY_CONTACT_1, SensorType.DRY_CONTACT_2] and self._device_class not in [DeviceClass.SENSORS_IN_ONE,DeviceClass.TWELVE_IN_ONE]:
            rdcs = _ReadDryContactStatus(self._buspro)
            rdcs.subnet_id, rdcs.device_id = self._device_address
            rdcs.switch_number = self._switch_number
            await rdcs.send()
        elif self._device_class == DeviceClass.SENSORS_IN_ONE:
            rsios = _ReadSensorsInOneStatus(self._buspro)
            rsios.subnet_id, rsios.device_id = self._device_address
            await rsios.send()
        else:
            rss = _ReadSensorStatus(self._buspro)
            rss.subnet_id, rss.device_id = self._device_address
            await rss.send()

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
        if self._motion_sensor == 1 or self._sonic == 1:
            return True
        if self._motion_sensor == 0 and self._sonic == 0:
            return False

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


    @property
    def device_identifier(self):
        device_class = self._device_class.value if self._device_class is not None else 'N'
        sensor_type = self._sensor_type.value if self._sensor_type is not None else 'N'
        universal_switch_number = self._universal_switch_number if self._universal_switch_number is not None else 'N'
        channel_number = self._channel_number if self._channel_number is not None else 'N'
        switch_number = self._switch_number if self._switch_number is not None else 'N'
        return f"{self._device_address}-{device_class}-{sensor_type}-{universal_switch_number}-{channel_number}-{switch_number}"

    def _call_read_current_status_of_sensor(self, run_from_init=False):

        async def read_current_status_of_sensor():
            if run_from_init:
                await asyncio.sleep(5)
            await self.read_sensor_status()

        asyncio.ensure_future(read_current_status_of_sensor(), loop=self._buspro.loop)
