# HDL Buspro

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

The HDL Buspro integration allows you to control your HDL Buspro system from Home Assistant.

## Installation
Under HACS -> Integrations, add custom repository "https://github.com/MyMight/home_assistant_buspro/" with Category "Integration". Select the integration named "HDL Buspro" and download it.

Restart Home Assistant.

Go to Settings > Integrations and Add Integration "HDL Buspro". Type in IP address and port number of the gateway.

## Configuration

#### Light platform
   
To use your Buspro light in your installation, add the following to your configuration.yaml file: 

```yaml
light:
  - platform: buspro
    running_time: 3
    devices:
      "1.89.1":
        name: Living Room Light
        running_time: 5
      "1.89.2":
        name: Front Door Light
        dimmable: False
```
+ **running_time** _(int) (Optional)_: Default running time in seconds for all devices. Running time is 0 seconds if not set.
+ **devices** _(Required)_: A list of devices to set up
  + **X.X.X** _(Required)_: The address of the device on the format `<subnet ID>.<device ID>.<channel number>`
    + **name** _(string) (Required)_: The name of the device
    + **running_time** _(int) (Optional)_: The running time in seconds for the device. If omitted, the default running time for all devices is used.
    + **dimmable** _(boolean) (Optional)_: Is the device dimmable? Default is True. 
    + **scan_interval** _(int) (Optional)_: Polling interval in seconds. Default is 0 (updates handled by system's background polling). Set a specific interval only for entities where you need guaranteed update frequency, as frequent polling of many entities may impact system performance.

#### Switch platform

To use your Buspro switch in your installation, add the following to your configuration.yaml file: 

```yaml
switch:
  - platform: buspro
    devices:
      "1.89.1":
        name: Living Room Switch
      "1.89.2":
        name: Front Door Switch
```
+ **devices** _(Required)_: A list of devices to set up
  + **X.X.X** _(Required)_: The address of the device on the format `<subnet ID>.<device ID>.<channel number>`
    + **name** _(string) (Required)_: The name of the device
    + **scan_interval** _(int) (Optional)_: Polling interval in seconds. Default is 0 (updates handled by system's background polling). Set a specific interval only for entities where you need guaranteed update frequency, as frequent polling of many entities may impact system performance.

It is also possible to use the switch to control buttons on control panels (switches) on the wall.
For this, you need to specify the `device` parameter as `panel`.

```yaml
switch:
  - platform: buspro
    devices:
      "1.79.1":
        name: Living Room Panel Button 1
        device: panel        # Panel device type
      "1.79.2": 
        name: Relay Switch Channel
        device: relay       # Relay device type (default)
        type: relay        # Relay switch type (default)
      "1.79.3":
        name: Universal Switch
        device: relay      # Relay device type
        type: universal_switch  # Universal switch type
```

#### Sensor platform

To use your Buspro sensor in your installation, add the following to your configuration.yaml file: 

```yaml
sensor:
  - platform: buspro
    devices:
      - address: "1.74"
        name: Living Room
        type: temperature
        device: dlp
      - address: "1.74"
        name: Front Door
        type: illuminance
        unit_of_measurement: lux
      - address: "1.31"
        name: Outdoor sensor
        type: temperature
        offset: -20
        device: sensors_in_one
      - address: "1.31.1"  # Power meter phase 1
        name: "Power Meter P1"
        type: active_power
      - address: "1.31.1"
        name: "Power Meter P1 Reactive"
        type: reactive_power
      - address: "1.31.1"
        name: "Power Meter P1 Apparent" 
        type: apparent_power
      - address: "1.31.1"
        name: "Power Meter P1 Voltage"
        type: voltage
      - address: "1.31.1"
        name: "Power Meter P1 Current"
        type: current
      - address: "1.31.1"
        name: "Power Meter P1 Energy"
        type: energy
      - address: "1.31.1"
        name: "Power Meter P1 Power Factor"
        type: power_factor
```
+ **devices** _(Required)_: A list of devices to set up
  + **address** _(string) (Required)_: The address of the sensor device on the format `<subnet ID>.<device ID>`
  + **name** _(string) (Required)_: The name of the device
  + **type** _(string) (Required)_: Type of sensor to monitor.
    + Available sensors:
      + temperature
      + humidity
      + illuminance
  + **unit_of_measurement** _(string) (Optional)_: text to be displayed as unit of measurement
  + **device** _(string) (Optional)_: The type of HDL sensor device
    + Available device families:
      + 12in1
      + sensors_in_one (devices like 8 in 1 and 7 in 1)
      + panel
      + dlp
  + **offset** _(int) (Optional)_: Offset to be added to the sensor value. Some devices, like HDL-MSOUT.4W, require an offset of -20.

The power meter sensors support the following types:
- `voltage` - Line voltage in Volts (V)
- `current` - Line current in Amperes (A)  
- `active_power` - Active/Real power in Watts (W)
- `reactive_power` - Reactive power in Volt-amperes reactive (VAr)
- `apparent_power` - Apparent power in Volt-amperes (VA)
- `power_factor` - Power factor as percentage (%)
- `energy` - Total energy consumption in kilowatt-hours (kWh)

For power meters with multiple phases, use channel numbers 1-3 for individual phases and channel 4 for total values (where supported by the device).

#### Binary sensor platform

To use your Buspro binary sensor in your installation, add the following to your configuration.yaml file: 

```yaml
binary_sensor:
  - platform: buspro
    devices:
      - address: "1.74"
        name: Living Room
        type: motion        
      - address: "1.74.100"
        name: Front Door
        type: universal_switch
      - address: "1.75.3"
        name: Kitchen switch
        type: single_channel
```
+ **devices** _(Required)_: A list of devices to set up
  + **address** _(string) (Required)_: The address of the sensor device on the format `<subnet ID>.<device ID>`. If 
  'type' = 'universal_switch' universal switch number must be appended to the address. 
  + **name** _(string) (Required)_: The name of the device
  + **type** _(string) (Required)_: Type of sensor to monitor.
    + Available sensors:
      + motion
      + dry_contact_1
      + dry_contact_2
      + universal_switch
      + single_channel
  + **device** _(string) (Optional)_: The type of HDL sensor device
    + Available device families:
      + 12in1
      + sensors_in_one (devices like 7 in 1)
  + **scan_interval** _(int) (Optional)_: Polling interval in seconds. Default is 0 (updates handled by system's background polling). Set a specific interval only for entities where you need guaranteed update frequency, as frequent polling of many entities may impact system performance.

#### Climate platform

To use your Buspro climate control in your installation, add the following to your configuration.yaml file: 

```yaml
climate:
  - platform: buspro
    devices:
      - address: "1.21.1"
        name: Bathroom Floor Heating
        device: floor_heating
        preset_modes:         # Optional preset modes
          - none              # Normal mode
          - away              # Away mode 
          - home              # Day mode
          - sleep             # Night mode
          - eco               # Timer mode (automatic day/night switching)
        hvac_modes:           # Optional heating/cooling modes
          - heat              # Heating only mode
        scan_interval: 60     # Optional polling interval
```
+ **devices** _(Required)_: A list of devices to set up
  + **address** _(string) (Required)_: The device address format depends on device type:
    + For Floor Heating: `<subnet ID>.<device ID>.<channel>` where channel is heating zone number (e.g. "1.21.1")
  + **name** _(string) (Required)_: The name of the device
  + **device** _(string) (Required)_: Type of climate device. Available types:
    + `floor_heating` - Floor Heating Module
  + **preset_modes** _(list) (Optional)_: List of supported preset modes. Preset mode selection is disabled if not set. Possible values are shown in table below. Corresponding modes must be enabled in HDL (Floor Heating > Working Settings > Mode).
  + **hvac_modes** _(list) (Optional)_: List of supported HVAC modes. Possible values:
    + `heat` - Heating mode
    + `cool` - Cooling mode
    Note: OFF mode is always available. If not configured, all supported modes will be enabled.
  + **scan_interval** _(int) (Optional)_: Polling interval in seconds.

| Home Assistant | HDL Buspro |
|---------------|------------|
| none          | Normal     |
| home          | Day        |
| sleep         | Night      |
| away          | Away       |
| eco           | Timer      |

The ECO preset mode uses HDL Timer mode where temperature is automatically switched between day and night settings according to schedule configured in HDL system. Manual temperature control is disabled in ECO mode.

#### Button platform

To use HDL Buspro buttons in your installation, add the following to your configuration.yaml file:

```yaml
button:
  - platform: buspro
    devices:
      "200.2.1.on":     # subnet.device.button.state
        name: "Button 1 ON"
      "200.2.1.off":
        name: "Button 1 OFF"
      "200.2.2.on":
        name: "Button 2 ON"
```

+ **devices** _(Required)_: A list of devices to set up
  + **X.X.X.state** _(Required)_: The address of the button in format `<subnet ID>.<device ID>.<button number>.<state>`
    + **subnet ID** - subnet number (1-255)
    + **device ID** - device number (1-255)
    + **button number** - button number (1-255)
    + **state** - `on` or `off` (determines the value sent when pressed)
    + **name** _(string) (Required)_: The name of the button

When pressed, the button sends panel control command with the configured state value to the specified device address.

#### Cover platform

To use your Buspro covers in your installation, add the following to your configuration.yaml file:

```yaml
cover:
  - platform: buspro
    devices:
      - address: "1.89.1"  # subnet.device.channel
        name: Living Room Blinds        
      - address: "1.90.2"
        name: Bedroom Blinds
        invert: true  # Invert open/close behavior
```

The cover platform supports the following features:
- Opening and closing operations
- Stop command to halt movement
- Tilt functionality using precise step control
  - Small upward step (tilt up)
  - Small downward step (tilt down)

Configuration parameters:
+ **devices** _(Required)_: A list of devices to set up
  + **address** _(string) (Required)_: The address of the device in format `<subnet ID>.<device ID>.<channel>` where:
    + **subnet ID** - subnet number (1-255)
    + **device ID** - device number (1-255)
    + **channel** - channel number (1-2, one device can control 2 covers)
  + **name** _(string) (Required)_: The name of the device
  + **invert** _(boolean) (Optional)_: Inverts the position reporting and control:
    - Default (false): 0=closed, 100=open
    - Inverted (true): 0=open, 100=closed

The cover platform supports:
- Full open/close control
- Stop function
- Small step movement mapped as tilt control

#### Security Module

To use your HDL Buspro security module in your installation, add the following to your configuration.yaml file:

```yaml
alarm_control_panel:
  - platform: buspro
    devices:
      - address: "1.89.1"  # subnet.device.area
        name: "Home Security"
        scan_interval: 60        
      - address: "1.89.2"
        name: "Office Security"        
```

The security module supports the following features:
- Disarming the alarm system
- Arming in multiple modes (home, away, night, vacation, etc.)

Configuration parameters:
+ **devices** _(Required)_: A list of devices to set up
  + **address** _(string) (Required)_: The address of the device in format `<subnet ID>.<device ID>.<area>`  
    + **device ID** - device number (1-255)
    + **area** - area ID (1-8)
    + **name** _(string) (Required)_: The name of the security module area
    + **scan_interval** _(int) (Optional)_: Polling interval in seconds. Default is 0 (updates handled by system's background polling). Set a specific interval only for entities where you need guaranteed update frequency, as frequent polling of many entities may impact system performance.


**Important**: You must configure your HDL security module to allow access from the Home Assistant integration device address (254.253). This permission should be set in HDL Buspro Setup Tool.

The alarm control panel supports the following states, mapped to HDL Buspro security module states:

| Home Assistant State | HDL Buspro State     |
|----------------------|----------------------|
| DISARMED             | Disarm               |
| ARMED_HOME           | Day Arm              |
| ARMED_NIGHT          | Night Arm            |
| ARMED_AWAY           | Away Arm             |
| ARMED_VACATION       | Vacation Arm         |
| ARMED_CUSTOM_BYPASS  | Night with Guest Arm |

The security module offers comprehensive alarm management capabilities that integrate directly with the HDL Buspro security subsystem.

---
## Services

#### Sending an arbitrary message:
```yaml
Domain: buspro
Service: send_message
Service Data: {"address": [1,74], "operate_code": [4,78], "payload": [1,100,0,3]}
```
#### Activating a scene:
```yaml
Domain: buspro
Service: activate_scene
Service Data: {"address": [1,74], "scene_address": [3,5]}
```
#### Setting an universal switch:
```yaml
Domain: buspro
Service: set_universal_switch
Service Data: {"address": [1,74], "switch_number": 100, "status": 1}
```
#### Synchronizing time with modules:
```yaml
Domain: buspro
Service: sync_time
Service Data: {"address": [1,74]}
```

This service can be used to synchronize time with HDL Buspro modules that support time synchronization (like security modules or logic modules). To automatically sync time every hour, add the following to your automations.yaml file:

```yaml
- id: hdl_time_sync
  alias: Sync time with HDL modules
  description: Synchronize time with HDL modules (security and logic module)
  triggers:
  - hours: /1
    trigger: time_pattern
  actions:
  - data:
      address:
      - 1
      - 12
    action: buspro.sync_time
  - data:
      address:
      - 1
      - 14
    action: buspro.sync_time    
```

