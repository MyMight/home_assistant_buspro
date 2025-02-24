"""HDL Buspro cover device implementation."""
from enum import IntEnum
import logging
from typing import Tuple

from custom_components.buspro.pybuspro.devices.control import _CurtainReadStatus, _CurtainSwitchControl
from ..helpers.enums import OperateCode
from .device import Device

_LOGGER = logging.getLogger(__name__)

class CoverCommand(IntEnum):
    """Cover control commands."""
    STOP = 0
    OPEN = 1
    CLOSE = 2
    STEP_OPEN = 3    # Small step up
    STEP_CLOSE = 4  # Small step down

class CoverStatus(IntEnum):
    """Cover position status."""
    STOP = 0
    OPEN = 1
    CLOSE = 2

class Cover(Device):
    """HDL Buspro cover device."""
    
    def __init__(self, buspro, device_address: Tuple[int, int], channel: int, name=""):
        super().__init__(buspro, device_address, name)
        """Initialize cover device.
        
        Args:
            buspro: HDL Buspro instance
            device_address: Tuple of (subnet_id, device_id)
            channel: Channel number (1-2)
        """
        self._buspro = buspro
        self._device_address = device_address
        self._channel = channel        
        self._position = 0
        self._status = CoverStatus.STOP
        self.register_telegram_received_cb(self._telegram_received_cb)

    def _telegram_received_cb(self, telegram):
        """Handle received telegram."""        
        if telegram.operate_code in [OperateCode.CurtainSwitchControlResponse, OperateCode.ReadStatusofCurtainSwitchResponse]:
            if telegram.payload[0] == self._channel and telegram.payload[0] in [CoverCommand.STOP, CoverCommand.OPEN, CoverCommand.CLOSE]:
                self._status = CoverStatus(telegram.payload[1])
                self._call_device_updated()

    async def read_cover_status(self):
        """Read current status from device."""
        csc = _CurtainReadStatus(self._buspro)        
        csc.channel = self._channel
        csc.subnet_id = self._device_address[0]
        csc.device_id = self._device_address[1]        
        await csc.send()

    async def _send_command(self, command: CoverCommand):
        """Send command to cover device."""
        csc = _CurtainSwitchControl(self._buspro)
        csc.channel = self._channel
        csc.state = CoverStatus.STOP
        csc.subnet_id = self._device_address[0]
        csc.device_id = self._device_address[1]
        
        if command in [CoverCommand.STEP_OPEN, CoverCommand.STEP_CLOSE]:
            csc.channel += 2
        
        if command in [CoverCommand.OPEN, CoverCommand.STEP_OPEN]:
            csc.state = CoverStatus.OPEN
        elif command in [CoverCommand.CLOSE, CoverCommand.STEP_CLOSE]:
            csc.state = CoverStatus.CLOSE
        _LOGGER.debug(f"Cover command:{self._device_address} {csc.channel} {csc.state}")
        await csc.send()

    async def stop(self):
        """Stop cover movement."""
        await self._send_command(CoverCommand.STOP)

    async def open_cover(self):
        """Open the cover."""
        await self._send_command(CoverCommand.OPEN)

    async def close_cover(self):
        """Close the cover."""
        await self._send_command(CoverCommand.CLOSE)

    async def small_step_open(self):
        """Tilt cover up (small movement)."""
        await self._send_command(CoverCommand.STEP_OPEN)

    async def small_step_close(self):
        """Tilt cover down (small movement)."""
        await self._send_command(CoverCommand.STEP_CLOSE)

    @property
    def position(self):
        """Return current position."""
        return self._position

    @property
    def is_moving(self):
        """Return True if cover is moving."""
        return self._status != CoverStatus.STOPPED


