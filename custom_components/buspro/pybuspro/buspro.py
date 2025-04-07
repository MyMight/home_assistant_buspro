''' pybuspro version 1.0.0  '''

import asyncio
import logging

from .helpers.enums import *
from .transport.network_interface import NetworkInterface
_LOGGER = logging.getLogger(__name__)

# ip, port = gateway_address
# subnet_id, device_id, channel = device_address
class Buspro:

    def __init__(self, hass, gateway_address_send_receive, loop_=None):
        self.loop = loop_ or asyncio.get_event_loop()
        self._hass = hass
        self.state_updater = None
        self.started = False
        self.network_interface = None
        self.logger = logging.getLogger("buspro.log")
        self.telegram_logger = logging.getLogger("buspro.telegram")

        self.callback_all_messages = None        
        self._telegram_received_cbs = {}

        self.gateway_address_send_receive = gateway_address_send_receive
        if _LOGGER.isEnabledFor(logging.DEBUG):
            _LOGGER.debug(f"Buspro logger level: {self.logger.getEffectiveLevel()}")
            _LOGGER.debug(f"Buspro telegram logger level: {self.telegram_logger.getEffectiveLevel()}")
        

    def __del__(self):
        if self.started:
            try:
                task = self.loop.create_task(self.stop())
                self.loop.run_until_complete(task)
            except RuntimeError as exp:
                self.logger.warning("Could not close loop, reason: {}".format(exp))

    # noinspection PyUnusedLocal
    async def start(self):
        self.network_interface = NetworkInterface(self._hass, self.gateway_address_send_receive)
        self.network_interface.register_callback(self._callback_all_messages)
        await self.network_interface.start()
        self.started = True

    async def stop(self):
        await self._stop_network_interface()
        self.started = False

    def _callback_all_messages(self, telegram):
        if self.telegram_logger.isEnabledFor(logging.DEBUG):
            self.telegram_logger.debug(telegram)

        if self.callback_all_messages is not None:
            self.callback_all_messages(telegram)
        
        callbacks_to_call = []
        
        if telegram.source_address in self._telegram_received_cbs:
            callbacks_to_call.extend(self._telegram_received_cbs[telegram.source_address])
            
#        if telegram.target_address in self._telegram_received_cbs:
#            callbacks_to_call.extend(self._telegram_received_cbs[telegram.target_address])
            

        for callback in set(callbacks_to_call):
            if telegram.operate_code is not OperateCode.BroadcastSystemDateandTimeEveryMinute:
                callback(telegram)

    async def _stop_network_interface(self):
        if self.network_interface is not None:
            await self.network_interface.stop()
            self.network_interface = None

    def register_telegram_received_all_messages_cb(self, telegram_received_cb):
        self.callback_all_messages = telegram_received_cb

    def register_telegram_received_device_cb(self, telegram_received_cb, device_address):
        """Registrace callbacku pro dané zařízení."""
        if not isinstance(device_address, tuple):
            device_address = tuple(device_address)
        
        if device_address not in self._telegram_received_cbs:
            self._telegram_received_cbs[device_address] = []
        
        if telegram_received_cb not in self._telegram_received_cbs[device_address]:
            self._telegram_received_cbs[device_address].append(telegram_received_cb)
        
    def unregister_telegram_received_device_cb(self, telegram_received_cb, device_address):
        """Zrušení registrace callbacku."""
        if not isinstance(device_address, tuple):
            device_address = tuple(device_address)
        
        if device_address in self._telegram_received_cbs:
            try:
                self._telegram_received_cbs[device_address].remove(telegram_received_cb)
                
                if not self._telegram_received_cbs[device_address]:
                    del self._telegram_received_cbs[device_address]
            except ValueError:                
                pass

