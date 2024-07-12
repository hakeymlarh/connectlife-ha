import yaml
from collections import defaultdict
import logging
import pkgutil

from connectlife.appliance import ConnectLifeAppliance
from homeassistant.const import Platform
from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.humidifier import HumidifierDeviceClass
from homeassistant.components.number import NumberDeviceClass
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.components.switch import SwitchDeviceClass
from homeassistant.components.water_heater import STATE_OFF

from .const import (
    ACTION,
    CURRENT_OPERATION,
    FAN_MODE,
    HVAC_ACTION,
    HVAC_MODE,
    IS_AWAY_MODE_ON,
    MODE,
    STATE,
    SWING_MODE,
    TEMPERATURE_UNIT,
)

DEVICE_CLASS = "device_class"
HIDE = "hide"
ICON = "icon"
OFF = "off"
ON = "on"
OPTIONS = "options"
PROPERTY = "property"
PROPERTIES = "properties"
MAX_VALUE = "max_value"
MIN_VALUE = "min_value"
TARGET = "target"
READ_ONLY = "read_only"
STATE_CLASS = "state_class"
SWITCH = "switch"
UNKNOWN_VALUE = "unknown_value"
UNIT = "unit"

_LOGGER = logging.getLogger(__name__)


class BinarySensor:
    device_class: BinarySensorDeviceClass | None

    def __init__(self, name: str, binary_sensor: dict | None):
        if binary_sensor is None:
            binary_sensor = {}
        self.device_class = BinarySensorDeviceClass(binary_sensor[DEVICE_CLASS]) \
            if DEVICE_CLASS in binary_sensor else None


class Climate:
    target: str
    options: dict | None
    unknown_value: int | None
    min_value: int | dict[str, int]
    max_value: int | dict[str, int]

    def __init__(self, name: str, climate: dict | None):
        if climate is None:
            climate = {}
        self.target = climate[TARGET] if TARGET in climate else None
        if self.target is None:
            _LOGGER.warning("Missing climate.target for for %s", name)
        self.options = climate[OPTIONS] if OPTIONS in climate else None
        if self.options is None and self.target in [FAN_MODE, HVAC_ACTION, HVAC_MODE, SWING_MODE, TEMPERATURE_UNIT]:
            _LOGGER.warning("Missing climate.options for %s", name)
        self.unknown_value = climate[UNKNOWN_VALUE] if UNKNOWN_VALUE in climate and climate[UNKNOWN_VALUE] else None
        self.min_value = climate[MIN_VALUE] if MIN_VALUE in climate else None
        self.max_value = climate[MAX_VALUE] if MAX_VALUE in climate else None


class Humidifier:
    target: str
    options: dict | None
    device_class: HumidifierDeviceClass | None
    min_value: int
    max_value: int

    def __init__(self, name: str, humidifier: dict | None):
        if humidifier is None:
            humidifier = {}
        self.target = humidifier[TARGET] if TARGET in humidifier else None
        if self.target is None:
            _LOGGER.warning("Missing humidifier.target for for %s", name)
        self.options = humidifier[OPTIONS] if OPTIONS in humidifier else None
        if self.options is None and self.target in [ACTION, MODE]:
            _LOGGER.warning("Missing humidifier.options for %s", name)
        self.device_class = HumidifierDeviceClass(humidifier[DEVICE_CLASS]) if DEVICE_CLASS in humidifier else None
        self.min_value = humidifier[MIN_VALUE] if MIN_VALUE in humidifier else None
        self.max_value = humidifier[MAX_VALUE] if MAX_VALUE in humidifier else None


class Number:
    min_value: int | None
    max_value: int | None
    device_class: NumberDeviceClass | None
    unit: str | None
    options: list[dict[int, str]] | None

    def __init__(self, name: str, sensor: dict):
        if sensor is None:
            sensor = {}
        self.unknown_value = sensor[UNKNOWN_VALUE] if UNKNOWN_VALUE in sensor and sensor[UNKNOWN_VALUE] else None
        self.min_value = sensor[MIN_VALUE] if MIN_VALUE in sensor else None
        self.max_value = sensor[MAX_VALUE] if MAX_VALUE in sensor else None
        self.unit = sensor[UNIT] if UNIT in sensor and sensor[UNIT] else None
        self.state_class = SensorStateClass(sensor[STATE_CLASS]) if STATE_CLASS in sensor else None

        device_class = None
        if DEVICE_CLASS in sensor:
            device_class = SensorDeviceClass(sensor[DEVICE_CLASS])
            if device_class == SensorDeviceClass.ENUM:
                if self.unit:
                    _LOGGER.warning("%s has device class enum, but has unit", name)
                    device_class = None
                if self.state_class:
                    _LOGGER.warning("%s has device class enum, but has state_class", name)
                    device_class = None
                if device_class and "options" not in sensor:
                    _LOGGER.warning("%s has device class enum, but no options", name)
                    device_class = None
                else:
                    self.options = sensor["options"]
            elif device_class == NumberDeviceClass.PH or device_class == NumberDeviceClass.AQI:
                if self.unit:
                    _LOGGER.warning("%s has device class %s and unit %s", name, device_class, self.unit)
                    self.unit = None
            elif not self.unit:
                _LOGGER.warning("%s has device class, but no unit", name)
                device_class = None
        self.device_class = device_class


class Select:
    options: dict

    def __init__(self, name: str, select: dict):
        if select is None:
            select = {}
        if OPTIONS not in select:
            _LOGGER.warning("Select %s has no options", name)
            self.options = {}
        else:
            self.options = select[OPTIONS]


class Sensor:
    unknown_value: int | None
    min_value: int | None
    max_value: int | None
    read_only: bool | None
    state_class: SensorStateClass | None
    device_class: SensorDeviceClass | None
    unit: str | None
    options: list[dict[int, str]] | None

    def __init__(self, name: str, sensor: dict):
        if sensor is None:
            sensor = {}
        self.unknown_value = sensor[UNKNOWN_VALUE] if UNKNOWN_VALUE in sensor and sensor[UNKNOWN_VALUE] else None
        self.read_only = sensor[READ_ONLY] if READ_ONLY in sensor else None
        self.unit = sensor[UNIT] if UNIT in sensor and sensor[UNIT] else None
        self.state_class = SensorStateClass(sensor[STATE_CLASS]) if STATE_CLASS in sensor else None

        device_class = None
        if DEVICE_CLASS in sensor:
            device_class = SensorDeviceClass(sensor[DEVICE_CLASS])
            if device_class == SensorDeviceClass.ENUM:
                if self.unit:
                    _LOGGER.warning("%s has device class enum, but has unit", name)
                    device_class = None
                if self.state_class:
                    _LOGGER.warning("%s has device class enum, but has state_class", name)
                    device_class = None
                if device_class and "options" not in sensor:
                    _LOGGER.warning("%s has device class enum, but no options", name)
                    device_class = None
                else:
                    self.options = sensor["options"]
            elif device_class == SensorDeviceClass.PH or device_class == SensorDeviceClass.AQI:
                if self.unit:
                    _LOGGER.warning("%s has device class %s and unit %s", name, device_class, self.unit)
                    self.unit = None
            elif not self.unit:
                _LOGGER.warning("%s has device class, but no unit", name)
                device_class = None
        self.device_class = device_class


class Switch:
    device_class: SwitchDeviceClass | None
    off: int
    on: int

    def __init__(self, name: str, switch: dict):
        if switch is None:
            switch = {}
        self.device_class = SwitchDeviceClass(switch[DEVICE_CLASS])\
            if DEVICE_CLASS in switch else None
        self.off = switch[OFF] if OFF in switch else 0
        self.on = switch[ON] if ON in switch else 1


class WaterHeater:
    target: str
    options: dict | None
    unknown_value: int | None
    min_value: int | dict[str, int]
    max_value: int | dict[str, int]

    def __init__(self, name: str, water_heater: dict | None):
        if water_heater is None:
            water_heater = {}
        self.target = water_heater[TARGET] if TARGET in water_heater else None
        if self.target is None:
            _LOGGER.warning("Missing water_heater.target for for %s", name)
        self.options = water_heater[OPTIONS] if OPTIONS in water_heater else None
        if self.options is None and self.target in [CURRENT_OPERATION, IS_AWAY_MODE_ON, STATE, TEMPERATURE_UNIT]:
            _LOGGER.warning("Missing water_heater.options for %s", name)
        if self.target == STATE and STATE_OFF not in self.options.values():
            _LOGGER.warning("Missing state off for water_heater.options for %s", name)
        if self.target == STATE and len(self.options) < 2:
            _LOGGER.warning("Require at least 2 valid states in water_heater.options for %s", name)
        self.unknown_value = (
            water_heater[UNKNOWN_VALUE]
            if UNKNOWN_VALUE in water_heater and water_heater[UNKNOWN_VALUE]
            else None
        )
        self.min_value = water_heater[MIN_VALUE] if MIN_VALUE in water_heater else None
        self.max_value = water_heater[MAX_VALUE] if MAX_VALUE in water_heater else None


class Property:
    name: str
    icon: str | None
    hide: bool
    binary_sensor: BinarySensor
    climate: Climate
    humidifier: Humidifier
    number: Number
    sensor: Sensor
    select: Select
    switch: Switch
    water_heater: WaterHeater

    def __init__(self, entry: dict):
        self.name = entry[PROPERTY]
        self.icon = entry[ICON] if ICON in entry and entry[ICON] else None
        self.hide = entry[HIDE] == bool(entry[HIDE]) if HIDE in entry else False

        if Platform.BINARY_SENSOR in entry:
            self.binary_sensor = BinarySensor(self.name, entry[Platform.BINARY_SENSOR])
        elif Platform.CLIMATE in entry:
            self.climate = Climate(self.name, entry[Platform.CLIMATE])
        elif Platform.HUMIDIFIER in entry:
            self.humidifier = Humidifier(self.name, entry[Platform.HUMIDIFIER])
        elif Platform.NUMBER in entry:
            self.number = Number(self.name, entry[Platform.NUMBER])
        elif Platform.SENSOR in entry:
            self.sensor = Sensor(self.name, entry[Platform.SENSOR])
        elif Platform.SELECT in entry:
            self.select = Select(self.name, entry[Platform.SELECT])
        elif Platform.SWITCH in entry:
            self.switch = Switch(self.name, entry[Platform.SWITCH])
        elif Platform.WATER_HEATER in entry:
            self.water_heater = WaterHeater(self.name, entry[Platform.WATER_HEATER])
        else:
            self.sensor = Sensor(self.name, {})


class Dictionaries:
    """Data dictionary for a ConnectLife appliance"""

    dictionaries: dict[str, dict[str, Property]] = {}

    @classmethod
    def get_dictionary(cls, appliance: ConnectLifeAppliance) -> dict[str, Property]:
        key = f"{appliance.device_type_code}-{appliance.device_feature_code}"
        if key in Dictionaries.dictionaries:
            return Dictionaries.dictionaries[key]
        try:
            dictionary = defaultdict(lambda: Property({PROPERTY: "unknown_property", HIDE: True}))
            data = pkgutil.get_data(__name__, f"data_dictionaries/{key}.yaml")
            parsed = yaml.safe_load(data)
            for prop in parsed[PROPERTIES]:
                dictionary[prop[PROPERTY]] = Property(prop)
        except FileNotFoundError:
            _LOGGER.warning("No data dictionary found for %s (%s)", appliance.device_nickname, key)
            dictionary = defaultdict(
                lambda: Property(
                    {
                        PROPERTY: "unknown_device",
                        HIDE: True,
                        Platform.SENSOR: {STATE_CLASS: SensorStateClass.MEASUREMENT}
                    }
                )
            )
        Dictionaries.dictionaries[key] = dictionary
        return dictionary
