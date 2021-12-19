"""Representations of API data for HomeSeer devices as Python objects."""

import logging
from sys import modules
from typing import Callable, List, Optional, Tuple, Union

from .const import RELATIONSHIP_CHILD, RELATIONSHIP_ROOT, RELATIONSHIP_STANDALONE

CONTROL_USE_ON = 1
CONTROL_USE_OFF = 2
CONTROL_USE_DIM = 3
CONTROL_USE_STOP = 7
CONTROL_USE_HEAT_SETPOINT = 12
CONTROL_USE_COOL_SETPOINT = 13
CONTROL_USE_THERM_MODE_OFF = 14
CONTROL_USE_THERM_MODE_HEAT = 15
CONTROL_USE_THERM_MODE_COOL = 16
CONTROL_USE_LOCK = 18
CONTROL_USE_UNLOCK = 19
CONTROL_USE_FAN = 23
CONTROL_LABEL_LOCK = "Lock"
CONTROL_LABEL_UNLOCK = "Unlock"

SUPPORT_STATUS = 0
SUPPORT_ON = 1
SUPPORT_OFF = 2
SUPPORT_LOCK = 4
SUPPORT_UNLOCK = 8
SUPPORT_DIM = 16
SUPPORT_FAN = 32
SUPPORT_STOP = 64
SUPPORT_SETPOINT = 128
SUPPORT_THERM_MODES = 512

_LOGGER = logging.getLogger(__name__)


class HomeSeerStatusDevice:
    """
    Representation of a HomeSeer device with no controls (i.e. status only).
    Base representation for all other HomeSeer device objects.
    """

    def __init__(self, raw_data: dict, control_data: dict, request: Callable) -> None:
        self._raw_data = raw_data
        self._control_data = control_data
        self._request = request
        self._update_callback = None
        self._suppress_update_callback = False

    @property
    def ref(self) -> int:
        """Return the HomeSeer device ref of the device."""
        return int(self._raw_data["ref"])

    @property
    def name(self) -> str:
        """Return the name of the device."""
        return self._raw_data["name"]

    @property
    def location(self) -> str:
        """Return the location parameter of the device."""
        return self._raw_data["location"]

    @property
    def location2(self) -> str:
        """Return the location2 parameter of the device."""
        return self._raw_data["location2"]

    @property
    def value(self) -> Union[int, float]:
        """Return the value of the device."""
        if "." in str(self._raw_data["value"]):
            return float(self._raw_data["value"])
        return int(self._raw_data["value"])

    @property
    def status(self) -> str:
        """Return the status of the device."""
        return self._raw_data["status"]

    @property
    def device_type_string(self) -> Optional[str]:
        """Return the device type string of the device, or None for no type string (e.g. virtual device)."""
        if self._raw_data["device_type_string"]:
            return self._raw_data["device_type_string"]
        return None

    @property
    def last_change(self) -> str:
        """Return the last change of the device."""
        return self._raw_data["last_change"]

    @property
    def relationship(self) -> int:
        """
        Return the relationship of the device.
        2 = Root device (other devices may be part of this physical device)
        3 = Standalone (this is the only device that represents this physical device)
        4 = Child (this device is part of a group of devices that represent the physical device)
        """
        relationship = int(self._raw_data["relationship"])
        if relationship == RELATIONSHIP_ROOT:
            return RELATIONSHIP_ROOT
        elif relationship == RELATIONSHIP_CHILD:
            return RELATIONSHIP_CHILD
        elif relationship == RELATIONSHIP_STANDALONE:
            return RELATIONSHIP_STANDALONE
        return relationship

    @property
    def associated_devices(self) -> list:
        """
        A list of device reference numbers that are associated with this device.
        If the device is a Root device, the list contains the device reference numbers of the child devices.
        If the device is a Child device, the list will contain one device reference number of the root device.
        """
        return self._raw_data["associated_devices"]

    @property
    def interface_name(self) -> Optional[str]:
        """
        Return the name of the interface providing the device, or None for no interface (e.g. virtual device).
        Note: this parameter is present in the JSON API data but undocumented.
        """
        if self._raw_data["interface_name"]:
            return self._raw_data["interface_name"]
        return None

    def register_update_callback(
        self, callback: Callable, suppress_on_connection: bool = False
    ) -> None:
        """
        Register an update callback for the device, called when the device is updated by update_data.
        Set suppress_on_connection to True to suppress the callback on listener connect and disconnect.
        """
        self._suppress_update_callback = suppress_on_connection
        self._update_callback = callback

    def update_data(self, new_data: dict = None, connection_flag: bool = False) -> None:
        """Retrieve and cache updated data for the device from the HomeSeer JSON API."""
        if new_data is not None:
            _LOGGER.debug(
                f"Updating data for {self.location2} {self.location} {self.name} ({self.ref})"
            )
            self._raw_data = new_data

        if connection_flag and self._suppress_update_callback:
            return

        if self._update_callback is not None:
            self._update_callback()

    def get_params(self, value) -> dict:
        params = {"request": "controldevicebyvalue", "ref": self.ref, "value": value}
        return params

    async def set_value(self, value) -> None:
        params = self.get_params(value)
        await self._request("get", params=params)

class HomeSeerSetPointDevice(HomeSeerStatusDevice):
    """Representation of a HomeSeer device that has a set point control pairs."""

    def __init__(
        self, raw_data: dict, control_data: dict, request: Callable, set_min:float,set_max:float
    ) -> None:
        super().__init__(raw_data, control_data, request)
        self._set_min = set_min
        self._set_max = set_max

    async def set_setpoint(self, value: float) -> None:
        if self._set_min <= value and value <= self._set_max:
            await self.set_value(value)

class HomeSeerSwitchableDevice(HomeSeerStatusDevice):
    """Representation of a HomeSeer device that has On and Off control pairs."""

    def __init__(
        self, raw_data: dict, control_data: dict, request: Callable, on_value: int, off_value: int
    ) -> None:
        super().__init__(raw_data, control_data, request)
        self._on_value = on_value
        self._off_value = off_value

    @property
    def is_on(self) -> bool:
        """Return True if the device's current value is greater than its off value."""
        return self.value != self._off_value

    async def on(self) -> None:
        """Turn the device on."""
        await self.set_value(self._on_value)

    async def off(self) -> None:
        """Turn the device off."""
        await self.set_value(self._off_value)

class HomeSeerDimmableDevice(HomeSeerSwitchableDevice):
    """Representation of a HomeSeer device that has a Dim control pair."""

    def __init__(
        self, raw_data: dict, control_data: dict, request: Callable, on_value: int, off_value: int, dim_start_value:int, dim_end_value:int
    ) -> None:
        super().__init__(raw_data, control_data, request, on_value, off_value)
        self._dim_start_value = dim_start_value
        self._dim_end_value = dim_end_value

    @property
    def dim_supported(self) -> bool:
        return self._dim_start_value != self._dim_end_value

    @property
    def dim_range(self) -> int:
        return self._dim_end_value - self._dim_start_value

    @property
    def dim_percent(self) -> int:
        """Returns a number from 0 to 1 representing the current dim percentage."""
        if self.value == self._on_value:
            return 100
        if self.value == self._off_value:
            return 0
        if not self.dim_supported:
            return 0
        
        return 100 * (self.value - self._dim_start_value) / self.dim_range

    async def dim(self, percent: int) -> None:
        if not self.dim_supported:
            return

        """Dim the device on a scale from 0 to 100."""
        if percent < 0 or percent > 100:
            raise ValueError("Percent must be an integer from 0 to 100")

        step = (self.dim_range) / 100
        value = int(step * percent) + self._dim_start_value
        await self.set_value(value)

class HomeSeerCoverDevice(HomeSeerDimmableDevice):
    """Representation of a HomeSeer cover that has a Stop and/or Dim control pair."""

    def __init__(
        self, raw_data: dict, control_data: dict, request: Callable, on_value: int, off_value: int, stop_value: int, dim_start_value:int = 0, dim_end_value:int = 0
    ) -> None:
        super().__init__(raw_data, control_data, request, on_value, off_value, dim_start_value, dim_end_value)
        self._stop_value = stop_value

    async def stop(self) -> None:
        await self.set_value(self._stop_value)

class HomeSeerFanDevice(HomeSeerSwitchableDevice):
    """Representation of a HomeSeer device that has a Fan or DimFan control pair."""

    @property
    def speed_percent(self) -> float:
        """Returns a number from 0 to 1 representing the current speed percentage."""
        return self.value / self._on_value

    async def speed(self, percent: int) -> None:
        """Set the speed of the device on a scale from 0 to 100."""
        if percent < 0 or percent > 100:
            raise ValueError("Percent must be an integer from 0 to 100")

        value = int(self._on_value * (percent / 100))
        await self.set_value(value)

class HomeSeerLockableDevice(HomeSeerStatusDevice):
    """Representation of a HomeSeer device that has Lock and Unlock control pairs."""

    def __init__(
        self, raw_data: dict, control_data: dict, request: Callable, lock_value: int, unlock_value: int
    ) -> None:
        super().__init__(raw_data, control_data, request)
        self._lock_value = lock_value
        self._unlock_value = unlock_value

    @property
    def is_locked(self) -> bool:
        """Return True if the device is locked."""
        return self.value == self._lock_value

    async def lock(self) -> None:
        """Lock the device."""
        await self.set_value(self._lock_value)

    async def unlock(self) -> None:
        """Unlock the device."""
        await self.set_value(self._unlock_value)

class HomeSeerClimateDevice(HomeSeerSwitchableDevice):
    """Representation of a HomeSeer device that has Lock and Unlock control pairs."""

    def __init__(
        self, raw_data: dict, control_data: dict, request: Callable, on_value: int, off_value: int
    ) -> None:
        super().__init__(raw_data, control_data, request, on_value, off_value)

def get_device(
    raw_data: dict, control_data: dict, request: Callable
) -> Optional[
    Union[
        HomeSeerDimmableDevice,
        HomeSeerFanDevice,
        HomeSeerLockableDevice,
        HomeSeerStatusDevice,
        HomeSeerSwitchableDevice,
        HomeSeerCoverDevice,
        HomeSeerSetPointDevice
    ]
]:
    """
    Parses control_data to return an appropriate device object
    based on the control pairs detected for the device.
    On/Off = HomeSeerSwitchableDevice
    On/Off/Dim = HomeSeerDimmableDevice
    On/Off/Fan = HomeSeerFanDevice
    Lock/Unlock = HomeSeerLockableDevice
    other = HomeSeerStatusDevice
    """
    item = next((x for x in control_data if x["ref"] == raw_data["ref"]), None)
    supported_features = get_supported_features(item)
    return build_device(raw_data, item, request, supported_features)

def build_device(raw_data: dict, item: dict, request: Callable, supported_features: int) -> Optional[
    Union[
        HomeSeerDimmableDevice,
        HomeSeerFanDevice,
        HomeSeerLockableDevice,
        HomeSeerStatusDevice,
        HomeSeerSwitchableDevice,
        HomeSeerCoverDevice,
        HomeSeerSetPointDevice
    ]
]:
    if supported_features == SUPPORT_ON | SUPPORT_OFF:
        return build_switch_device(raw_data, item, request)
    elif supported_features == SUPPORT_ON | SUPPORT_OFF | SUPPORT_DIM:
        return build_dimmable_device(raw_data, item, request)
    elif supported_features == SUPPORT_ON | SUPPORT_OFF | SUPPORT_DIM | SUPPORT_STOP:
        return build_cover_device(raw_data, item, request)
    elif supported_features == SUPPORT_ON | SUPPORT_OFF | SUPPORT_STOP:
        return build_cover_device(raw_data, item, request)
    elif supported_features == SUPPORT_ON | SUPPORT_OFF | SUPPORT_FAN:
        return build_fan_device(raw_data, item, request)
    elif supported_features == SUPPORT_LOCK | SUPPORT_UNLOCK:
        return build_lockable_device(raw_data, item, request)
    elif supported_features == SUPPORT_SETPOINT:
        return build_setpoint_device(raw_data, item, request)
    else:
        _LOGGER.debug(
            f"Failed to automatically detect device Control Pairs for device ref {raw_data['ref']}; "
            f"creating a status-only device. "
            f"If this device has controls, open an issue on the libhomeseer repo "
            f"with the following information to request support for this device: "
            f"RAW: ({raw_data}) "
            f"CONTROL: ({item})."
        )
        return HomeSeerStatusDevice(raw_data, item, request)

def get_supported_features(control_item: dict) -> int:
    supported_features = SUPPORT_STATUS
    if control_item is None:
        return supported_features
    control_pairs = control_item["ControlPairs"]
    if control_pairs is None:
        return supported_features
    for pair in control_pairs:
        control_use = pair["ControlUse"]
        if control_use == CONTROL_USE_ON:
            supported_features |= SUPPORT_ON
        elif control_use == CONTROL_USE_OFF:
            supported_features |= SUPPORT_OFF
        elif control_use == CONTROL_USE_STOP:
            supported_features |= SUPPORT_STOP
        elif (control_use == CONTROL_USE_LOCK):
            supported_features |= SUPPORT_LOCK
        elif (control_use == CONTROL_USE_UNLOCK):
            supported_features |= SUPPORT_UNLOCK
        elif control_use == CONTROL_USE_DIM:
            supported_features |= SUPPORT_DIM
        elif control_use == CONTROL_USE_FAN:
            supported_features |= SUPPORT_FAN
        elif control_use == CONTROL_USE_COOL_SETPOINT or control_use == CONTROL_USE_HEAT_SETPOINT:
            supported_features |= SUPPORT_SETPOINT
        elif control_use == CONTROL_USE_THERM_MODE_COOL or control_use == CONTROL_USE_THERM_MODE_HEAT or control_use == CONTROL_USE_THERM_MODE_OFF:
            supported_features |= SUPPORT_THERM_MODES
    return supported_features

def build_setpoint_device(raw_data: dict, control_item: dict, request: Callable) -> HomeSeerSetPointDevice:
    pair = get_control_pair_by_control_use(control_item, CONTROL_USE_COOL_SETPOINT)
    if pair is None:
        pair = get_control_pair_by_control_use(control_item, CONTROL_USE_HEAT_SETPOINT)
    (start, end) = get_range(pair)
    return HomeSeerSetPointDevice(raw_data, control_item, request, start, end)

def build_lockable_device(raw_data: dict, control_item: dict, request: Callable) -> HomeSeerLockableDevice:
    lock_value = get_control_value_by_control_use(control_item, CONTROL_USE_LOCK)
    unlock_value = get_control_value_by_control_use(control_item, CONTROL_USE_UNLOCK)
    return HomeSeerLockableDevice(raw_data, control_item, request, lock_value, unlock_value)

def build_switch_device(raw_data: dict, control_item: dict, request: Callable) -> HomeSeerSwitchableDevice:
    on_value = get_control_value_by_control_use(control_item, CONTROL_USE_ON)
    off_value = get_control_value_by_control_use(control_item, CONTROL_USE_OFF)
    return HomeSeerSwitchableDevice(raw_data, control_item, request, on_value, off_value)

def build_dimmable_device(raw_data: dict, control_item: dict, request: Callable) -> HomeSeerDimmableDevice:
    on_value = get_control_value_by_control_use(control_item, CONTROL_USE_ON)
    off_value = get_control_value_by_control_use(control_item, CONTROL_USE_OFF)
    (start_value, end_value) = get_range_for(control_item, CONTROL_USE_DIM)
    return HomeSeerDimmableDevice(raw_data, control_item, request, on_value, off_value, start_value, end_value)

def build_cover_device(raw_data: dict, control_item: dict, request: Callable) -> HomeSeerCoverDevice:
    on_value = get_control_value_by_control_use(control_item, CONTROL_USE_ON)
    off_value = get_control_value_by_control_use(control_item, CONTROL_USE_OFF)
    stop_value = get_control_value_by_control_use(control_item, CONTROL_USE_STOP)
    (start_value, end_value) = get_range_for(control_item, CONTROL_USE_DIM)
    return HomeSeerCoverDevice(raw_data, control_item, request, on_value, off_value, stop_value, start_value, end_value)

def build_fan_device(raw_data: dict, control_item: dict, request: Callable) -> HomeSeerFanDevice:
    on_value = get_control_value_by_control_use(control_item, CONTROL_USE_ON)
    off_value = get_control_value_by_control_use(control_item, CONTROL_USE_OFF)
    return HomeSeerFanDevice(raw_data, control_item, request, on_value, off_value)

def get_control_value_by_control_use(item: dict, control_use:int) -> Union[int,float, str, None]:
    control_pair = get_control_pair_by_control_use(item, control_use)
    if control_pair is not None:
        return control_pair["ControlValue"]
    return None

def get_control_pair_by_control_use(item: dict, control_use:int) -> Union[dict, None]:
    if item is None:
        return None
    control_pairs = item["ControlPairs"]
    control_pair = next((x for x in control_pairs if x["ControlUse"] == control_use), None)
    return control_pair

def get_range_for(control_item: dict, control_use:int) -> Union[Tuple[float, float], None]:
    pair = get_control_pair_by_control_use(control_item, control_use)
    return get_range(pair)

def get_range(control_pair:dict) -> Union[Tuple[float, float], None]:
    if control_pair is None:
        return (0,0)
    the_range = control_pair["Range"]
    start = the_range["RangeStart"]
    end = the_range["RangeEnd"]
    return (start, end)
   
def get_thermostat(thermostat: HomeSeerStatusDevice, devices: List[HomeSeerStatusDevice]) -> any:
    children_ids = thermostat._raw_data["associated_devices"]
    children = [dev for dev in devices if dev.ref in children_ids]

    mode = next((x for x in children if x.device_type_string == "Z-Wave Mode"), None)
    heater = next((x for x in children if x.device_type_string == "Z-Wave Switch"), None)
    heating_setpoint = next((x for x in children if x.device_type_string == "Z-Wave Heating  Setpoint"), None)
    cooling_setpoint = next((x for x in children if x.device_type_string == "Z-Wave Cooling  Setpoint"), None)
    energy_setpoint = next((x for x in children if x.device_type_string == "Z-Wave Energy Save Heating Setpoint"), None)
    air_temp = next((x for x in children if x.device_type_string == "Z-Wave Temperature" and x.name == "Thermostat Air Temperature"), None)
    floor_temp = next((x for x in children if x.device_type_string == "Z-Wave Temperature" and x.name == "Floor Temperature"), None)

    return None


