"""Scheduler for periodic reading of Buspro entities."""
from dataclasses import dataclass
import asyncio
import logging
import heapq
from datetime import timedelta
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.core import callback, HomeAssistant

_LOGGER = logging.getLogger(__name__)

@dataclass
class EntityInfo:
    """Entity information for scheduling."""
    scan_interval: int
    next_read_time: float
    entity_id: str

    def __lt__(self, other):
        """Enable heap comparison."""
        return self.next_read_time < other.next_read_time

class Scheduler:
    """Scheduler for periodic reading of entities."""
    def __init__(self, hass: HomeAssistant):
        self.hass = hass
        self._periodic_heap = []     # heap for entities with scan interval
        self._optional_heap = []    # heap for entities without scan interval
        self.entities_map = {}       # map for quick entity access
        self.default_read_interval = 10  # seconds
        self._now = self.hass.loop.time()
        self._cancel_timer = None

    async def add_entity(self, entity) -> None:
        """Add entity to scheduler.
        
        Args:
            entity: Entity to schedule for periodic updates.
                    Must implement async_update method.
        """
        entity_id = entity.entity_id
        
        if not hasattr(entity, 'async_update'):
            return
        
        scan_interval = entity.scan_interval
        
        if scan_interval is None or scan_interval == 0:
            seconds = 0
            target_heap = self._optional_heap
        else:
            try:
                seconds = int(scan_interval)
            except ValueError:
                _LOGGER.error(f"Invalid scan_interval for entity {entity_id}: {scan_interval}")
                seconds = self.default_read_interval
            target_heap = self._periodic_heap

        info = EntityInfo(
            scan_interval=seconds,
            next_read_time=self.hass.loop.time() + seconds,
            entity_id=entity_id
        )
        self.entities_map[entity_id] = info
        heapq.heappush(target_heap, info)
        if _LOGGER.isEnabledFor(logging.DEBUG):
            _LOGGER.debug(f"Added entity {entity_id} to scheduler (scan_interval={seconds}s)")

    async def read_entities_periodically(self) -> None:
        """Register periodic reading of entities."""
        @callback
        async def _process_entities(*_):
            self._now = self.hass.loop.time()
            
            # Process one entity with interval if available and due
            if self._periodic_heap and self._periodic_heap[0].next_read_time <= self._now:
                info = heapq.heappop(self._periodic_heap)
                await self.process_entity_reading(info.entity_id, info, info.scan_interval)
                # Reschedule
                info.next_read_time = self._now + info.scan_interval
                heapq.heappush(self._periodic_heap, info)
            # Process one immediate entity if no interval entity was processed
            elif self._optional_heap and self._optional_heap[0].next_read_time <= self._now:
                info = heapq.heappop(self._optional_heap)
                await self.process_entity_reading(info.entity_id, info, self.default_read_interval)
                # Reschedule
                info.next_read_time = self._now + self.default_read_interval
                heapq.heappush(self._optional_heap, info)

        self._cancel_timer = async_track_time_interval(
            self.hass,
            _process_entities,
            timedelta(seconds=1)
        )

    async def stop(self) -> None:
        """Stop the scheduler."""
        if self._cancel_timer:
            self._cancel_timer()

    async def process_entity_reading(self, entity_id: str, info: EntityInfo, interval: int) -> None:
        """Process entity reading."""
        if _LOGGER.isEnabledFor(logging.DEBUG):
            _LOGGER.debug(f"Entity {entity_id} is due for reading")
        try:
            _LOGGER.info(f"Reading data from entity {entity_id}")
            if self.hass.states.get(entity_id):
                await self.hass.services.async_call(
                    'homeassistant', 'update_entity', {'entity_id': entity_id}
                )
                if entity_id in self.entities_map:
                    self.entities_map[entity_id].next_read_time = self._now + interval
            else:
                _LOGGER.warning(f"Entity {entity_id} not found, removing from list")
                del self.entities_map[entity_id]
        except Exception as e:
            _LOGGER.error(f"Error reading entity {entity_id}: {e}")

    async def device_updated(self, entity_id: str, should_reschedule: bool = True) -> None:
        """Update next read time for entity if should_reschedule is True."""
        if entity_id not in self.entities_map:
            return
        
        # Reset scheduler only when requested
        if not should_reschedule:
            return

        current_time = self.hass.loop.time()
        if current_time - self._now > 1:
            self._now = current_time

        info = self.entities_map[entity_id]
        interval = info.scan_interval if info.scan_interval > 0 else self.default_read_interval
        info.next_read_time = self._now + interval
