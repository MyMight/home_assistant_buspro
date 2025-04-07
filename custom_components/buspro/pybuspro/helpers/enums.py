from enum import Enum, IntEnum
import voluptuous as vol

class OperateCode(Enum):
    NotSet = b'\x00'

    SingleChannelControl = b'\x00\x31'
    SingleChannelControlResponse = b'\x00\x32'
    ReadStatusOfChannels = b'\x00\x33'
    ReadStatusOfChannelsResponse = b'\x00\x34'
    SceneControl = b'\x00\x02'
    SceneControlResponse = b'\x00\x03'
    UniversalSwitchControl = b'\xE0\x1C'
    UniversalSwitchControlResponse = b'\xE0\x1D'

    ReadStatusOfUniversalSwitch = b'\xE0\x18'
    ReadStatusOfUniversalSwitchResponse = b'\xE0\x19'
    BroadcastStatusOfUniversalSwitch = b'\xE0\x17'

    Read12in1SensorStatus = b'\x16\x45'
    Read12in1SensorStatusResponse = b'\x16\x46'
    Broadcast12in1SensorStatusAutoResponse = b'\x16\x47'

    ReadSensorsInOneStatus = b'\x16\x04'
    ReadSensorsInOneStatusResponse = b'\x16\x05'
    BroadcastSensorsInOneStatusResponse = b'\x16\x30'

    BroadcastTemperatureResponse = b'\xE3\xE5'

    DLPReadFloorHeatingStatus = b'\x19\x44'
    DLPReadFloorHeatingStatusResponse = b'\x19\x45'
    DLPControlFloorHeatingStatus = b'\x19\x46'
    DLPControlFloorHeatingStatusResponse = b'\x19\x47'

    FHMReadFloorHeatingStatus = b'\x1C\x5E'
    FHMResponseReadFloorHeatingStatus = b'\x1C\x5F'
    FHMControlFloorHeatingStatus = b'\x1C\x5C'
    FHMResponseControlFloorHeatingStatus = b'\x1C\x5D'



    ReadDryContactStatus = b'\x15\xCE'
    ReadDryContactStatusResponse = b'\x15\xCF'
    ReadDryContactBroadcastStatusResponse = b'\x15\xD1'

    ReadTemperatureStatus = b'\xE3\xE7'
    ReadTemperatureStatusResponse = b'\xE3\xE8'

    ReadVoltage = b'\xD9\x02'
    ReadVoltageResponse  = b'\xD9\x03'

    ReadCurrent = b'\xD9\x08'
    ReadCurrentResponse  = b'\xD9\x09'

    ReadPowerStatus = b'\xD9\x0A'
    ReadPowerStatusResponse  = b'\xD9\x0B'

    ReadPowerFactorStatus = b'\xD9\x04'
    ReadPowerFactorStatusResponse = b'\xD9\x05'

    ReadElectricityStatus = b'\xD9\x1A'
    ReadElectricityStatusResponse = b'\xD9\x1B'
    

    PanelControl = b'\xE3\xD8'
    PanelControlResponse = b'\xE3\xD9'
    ReadPanelStatus = b'\xE3\xDA'
    ReadPanelStatusResponse = b'\xE3\xDB'

    CurtainSwitchControl = b'\xE3\xE0'
    CurtainSwitchControlResponse = b'\xE3\xE1'
    ReadStatusofCurtainSwitch = b'\xE3\xE2'
    ReadStatusofCurtainSwitchResponse = b'\xE3\xE3'

    ReadSecurityModule = b'\x01\x1E'
    ReadSecurityModuleResponse = b'\x01\x1F'
    ArmSecurityModule = b'\x01\x04'
    ArmSecurityModuleResponse = b'\x01\x05'
    AlarmSecurityModule = b'\x01\x0C'
    AlarmSecurityModuleResponse = b'\x01\x0D'

    ModifySystemDateandTime = b'\xDA\x02'



    BroadcastSystemDateandTimeEveryMinute = b'\xDA\x44'

    # b'\x1947'
    # INFO_IF_FROM_12in1__1 = b'\x16\x47'
    INFO_IF_FROM_RELE_10V = b'\xEF\xFF'
    # b'\xF036'

    QUERY_DLP_FROM_SETUP_TOOL_1 = b'\xE0\xE4'  # Ingen data sendes svar sendes sender
    RESPONSE_QUERY_DLP_FROM_SETUP_TOOL_1 = b'\xE0\xE5'
    QUERY_DLP_FROM_SETUP_TOOL_2 = b'\x19\x44'  # Ingen data sendes svar sendes sender			FLOOR HEATING WORKING STATUS
    RESPONSE_QUERY_DLP_FROM_SETUP_TOOL_2 = b'\x19\x45'
    QUERY_DLP_FROM_SETUP_TOOL_3 = b'\x19\x40'  # Ingen data sendes svar sendes sender			FLOOR HEATING
    RESPONSE_QUERY_DLP_FROM_SETUP_TOOL_3 = b'\x19\x41'
    QUERY_DLP_FROM_SETUP_TOOL_4 = b'\x19\x46'  # 0 1 1 23 20 20 20										FLOOR HEATING WORKING STATUS CONTROL
    RESPONSE_QUERY_DLP_FROM_SETUP_TOOL_4 = b'\x19\x47'
    # b'\x19\x48' Temperature request?
    # b'\x19\x49' Temperature request?
    # b'\xE3\xE5' GPRS control answer back

    QUERY_12in1_FROM_SETUP_TOOL_1 = b'\x00\x0E'
    RESPONSE_QUERY_12in1_FROM_SETUP_TOOL_1 = b'\x00\x0F'
    QUERY_12in1_FROM_SETUP_TOOL_2 = b'\xF0\x03'
    RESPONSE_QUERY_12in1_FROM_SETUP_TOOL_2 = b'\xF0\x04'
    QUERY_12in1_FROM_SETUP_TOOL_3 = b'\xDB\x3E'
    RESPONSE_QUERY_12in1_FROM_SETUP_TOOL_3 = b'\xDB\x3F'
    QUERY_12in1_FROM_SETUP_TOOL_4 = b'\x16\x66'
    RESPONSE_QUERY_12in1_FROM_SETUP_TOOL_4 = b'\x16\x67'
    QUERY_12in1_FROM_SETUP_TOOL_5 = b'\x16\x45'
    RESPONSE_QUERY_12in1_FROM_SETUP_TOOL_5 = b'\x16\x46'
    QUERY_12in1_FROM_SETUP_TOOL_6 = b'\x16\x5E'
    RESPONSE_QUERY_12in1_FROM_SETUP_TOOL_6 = b'\x16\x5F'
    QUERY_12in1_FROM_SETUP_TOOL_7 = b'\x16\x41'
    RESPONSE_QUERY_12in1_FROM_SETUP_TOOL_7 = b'\x16\x42'
    QUERY_12in1_FROM_SETUP_TOOL_8 = b'\x16\x6E'
    RESPONSE_QUERY_12in1_FROM_SETUP_TOOL_8 = b'\x16\x6F'
    QUERY_12in1_FROM_SETUP_TOOL_9 = b'\x16\xA9'
    RESPONSE_QUERY_12in1_FROM_SETUP_TOOL_9 = b'\x16\xAA'

class SuccessOrFailure(IntEnum):
    Success = 248 # 0xF8
    Failure = 245 # 0xF5


class DeviceType(Enum):
    PyBusPro = b'\xFF\xFC'
    NotSet = b'\x00\x00'
    SB_DN_6B0_10v = b'\x00\x11'   # Rele varme
    SB_DN_SEC250K = b'\x0B\xE9'   # Sikkerhetsmodul
    SB_CMS_12in1 = b'\x01\x34'    # 12i1
    SB_DN_Logic960 = b'\x04\x53'  # Logikkmodul
    SB_DLP2 = b'\x00\x86'         # DLP
    SB_DLP = b'\x00\x95'          # DLP
    SB_DLP_v2 = b'\x00\x9C'       # DLPv2    
    SmartHDLTest = b'\xFF\xFD'
    SetupTool = b'\xFF\xFE'
    SB_WS8M = b'\x01\x2B'         # 8 keys panel
    SB_CMS_8in1 = b'\x01\x35'     # 8i1
    SB_DN_DT0601 = b'\x02\x60'    # 6ch Dimmer
    HDL_MDT0601 = b'\x02\x6D'     # 6ch Dimmer ny type
    SB_DN_R0816 = b'\x01\xAC'     # Rele
    SB_DRY_4Z = b'\x00\x77'       # Dry contact
    HDL_MSP07M = b'\x01\x50'      # Sensors in One    

class OnOff(Enum):
    OFF = 0
    ON = 255


class SwitchStatusOnOff(Enum):
    OFF = 0
    ON = 1


class OnOffStatus(Enum):
    OFF = 0
    ON = 1


class TemperatureType(Enum):
    Celsius = 0
    Fahrenheit = 1


class TemperatureMode(Enum):
    Normal = 1
    Day = 2
    Night = 3
    Away = 4
    Timer = 5


class WorkType(Enum):
    """Work type modes for floor heating module."""
    HEATING = 0
    COOLING = 1
    HEATING_POWER = 2
    COOLING_POWER = 3


class OperationMode(Enum):
    """Operation modes for climate device."""
    NORMAL = 1
    DAY = 2
    NIGHT = 3
    AWAY = 4
    TIMER = 5


class DeviceFamily(str, Enum):
    TWELVE_IN_ONE = "12in1"
    DLP = "dlp"
    PANEL = "panel"
    SENSORS_IN_ONE = "sensors_in_one"
    RELAY = "relay"
    

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
    CURRENT = "current"
    VOLTAGE = "voltage"
    ACTIVE_POWER = "active_power"  # Only active power
    REACTIVE_POWER = "reactive_power"  # Reactive power (VAr)
    APPARENT_POWER = "apparent_power"  # Apparent power (VA)
    POWER_FACTOR = "power_factor"
    ENERGY = "energy"
    

class SwitchType(str, Enum):
    """Switch type enum."""
    RELAY = "relay"  # Standard relay switch
    UNIVERSAL_SWITCH = "universal_switch"  # Universal switch


def validate_device_family(value):
    """Validate device family value."""
    if value == "None":
        return value
    valid_values = [member.value for member in DeviceFamily]
    if value not in valid_values:
        raise vol.Invalid(f"Invalid device family: {value}. Valid values are: {', '.join(valid_values)}")
    return value
