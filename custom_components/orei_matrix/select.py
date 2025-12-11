from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN, EDID_LIST
from propcache.api import cached_property
import logging

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities):
    """Set up Orei HDMI Matrix input EDID assignments as selects."""
    data = hass.data[DOMAIN][entry.entry_id]
    client = data["client"]
    coordinator = data["coordinator"]
    config = data["config"]
    sources = config.get("sources", [])
    entities = [
        OreiMatrixInputEDID(client, coordinator, config, f"{source_name} EDID", idx, entry.entry_id)
        for idx, source_name in enumerate(sources, start=1)
    ]

    async_add_entities(entities)


class OreiMatrixInputEDID(CoordinatorEntity, SelectEntity):
    """Represents one HDMI matrix input as a select to adjust the assigned EDID."""

    def __init__(self, client, coordinator, config, name, input_id, entry_id) -> None:
        super().__init__(coordinator)
        self._client = client
        self._config = config
        self._attr_name = name
        self._input_id = input_id
        self._entry_id = entry_id
        self._attr_unique_id = f"{DOMAIN}_{config.get('host')}_{input_id}_edid"
        self._attr_options = EDID_LIST

    @property
    def device_info(self):
        """Device info for grouping and model-based naming."""
        model = self.coordinator.data.get("type", "Unknown")
        name = f"Orei {model}" if model != "Unknown" else "Orei HDMI Matrix"
        return {
            "identifiers": {(DOMAIN, self._entry_id)},
            "name": name,
            "manufacturer": "Orei",
            "model": model,
            "configuration_url": f"http://{self._config.get('host')}",
        }

    @property
    def current_option(self) -> str | None:
        """Return the selected entity option to represent the entity state."""
        return self._attr_current_option

    @callback
    def _handle_coordinator_update(self):
        edids = self.coordinator.data.get("edids")
        if not edids:
            return
        self._attr_current_option = edids[self._input_id]
        self.async_write_ha_state()

    async def async_select_option(self, option: str) -> None:
        """Set the new EDID for this input."""
        try:
            edid = EDID_LIST.index(option) + 1
        except ValueError:
            _LOGGER.warning("Could not find index of %s to set new EDID")
            return None

        await self._client.set_input_edid(self._input_id, edid)
        await self.coordinator.async_request_refresh()
        _LOGGER.info("Changed EDID of %s to %s", self.name, option)