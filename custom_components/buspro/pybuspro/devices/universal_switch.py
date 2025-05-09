import asyncio

from .control import _UniversalSwitch, _ReadStatusOfUniversalSwitch
from .device import Device
from ..helpers.enums import *


class UniversalSwitch(Device):
    def __init__(self, hass, device_address, switch_number, name="", delay_read_current_state_seconds=0):
        super().__init__(hass, device_address, name)
        # device_address = (subnet_id, device_id, switch_number)

        self._hass = hass
        self._device_address = device_address
        self._switch_number = switch_number
        self._switch_status = SwitchStatusOnOff.OFF
        self.register_telegram_received_cb(self._telegram_received_cb)
        self._call_read_current_status_of_universal_switch(run_from_init=True)

    def _telegram_received_cb(self, telegram):
        if telegram.operate_code in [OperateCode.UniversalSwitchControlResponse, OperateCode.ReadStatusOfUniversalSwitchResponse]:
            if self._switch_number == telegram.payload[0]:
                self._switch_status = SwitchStatusOnOff(telegram.payload[1])
                self._call_device_updated()
        elif telegram.operate_code == OperateCode.BroadcastStatusOfUniversalSwitch:
            if self._switch_number <= telegram.payload[0]:
                self._switch_status = SwitchStatusOnOff(telegram.payload[self._switch_number])
                self._call_device_updated(should_reschedule=False)  # Broadcast updates shouldn't reset scheduler

    async def set_on(self):
        await self._set(OnOff.ON)

    async def set_off(self):
        await self._set(OnOff.OFF)

    async def read_status(self):
        rsous = _ReadStatusOfUniversalSwitch(self._hass, self._device_address)
        rsous.switch_number = self._switch_number
        await rsous.send()

    @property
    def is_on(self):
        if self._switch_status == SwitchStatusOnOff.OFF:
            return False
        else:
            return True

    @property
    def device_identifier(self):
        return f"{self._device_address}-{self._switch_number}"

    async def _set(self, switch_status):
        self._switch_status = switch_status

        us = _UniversalSwitch(self._hass, self._device_address)        
        us.switch_number = self._switch_number
        us.switch_status = self._switch_status
        await us.send()

    def _call_read_current_status_of_universal_switch(self, run_from_init=False):

        async def read_current_state_of_universal_switch():
            if run_from_init:
                await asyncio.sleep(1)

            read_status_of_universal_switch = _ReadStatusOfUniversalSwitch(self._hass, self._device_address)            
            read_status_of_universal_switch.switch_number = self._switch_number
            await read_status_of_universal_switch.send()

        asyncio.ensure_future(read_current_state_of_universal_switch(), loop=self._hass.loop)
