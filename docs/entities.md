# Home Assistant Entities

## Sensors

| Key                                                   | Name                                    | Notes                            |
|-------------------------------------------------------|-----------------------------------------|----------------------------------|
| `adblue_range`                                        | AdBlue Range                            |                                  |
| `aux_estimated_time_left_to_reach_target_temperature` | Heater Time to reach target temperature |                                  |
| `car_captured`                                        | Last Updated                            | See (#last-updated-sensor)       |
| `charge_type`                                         | Charge Type                             | AC, DC                           |
| `charging_power`                                      | Charging Power                          | In kW                            |
| `charging_rate`                                       | Charging Rate                           | In km/h are being charged        |
| `charging_state`                                      | Charging State                          | Ready, Charging, Conserving, ... |
| `combustion_range`                                    | Combustion Range                        | For hybrids                      |
| `electric_range`                                      | Electric Range                          | For hybrids                      |
| `estimated_time_left_to_reach_target_temperature`     | Heater Time to reach target temperature |                                  |
| `fuel_level`                                          | Fuel Level                              |                                  |
| `gas_level`                                           | Gas Level                               | Fo CNG hybrids                   |
| `gas_range`                                           | Gas Range                               | For CNG hybrids                  |
| `inspection_in_km`                                    | Next Inspection                         |                                  |
| `inspection`                                          | Next Inspection                         |                                  |
| `milage`                                              | Mileage                                 |                                  |
| `oil_service_in_days`                                 | Oil Service                             |                                  |
| `oil_service_in_km`                                   | Oil Service                             |                                  |
| `operation`                                           | Last Operation                          | See (#last-operation)            |
| `outside_temperature`                                 | Outside Temperature                     |                                  |
| `range`                                               | Range                                   |                                  |
| `remaining_charging_time`                             | Remaining Charging Time                 |                                  |
| `service_event`                                       | Last Service Event                      | See (#last-service-event)        |
| `software_version`                                    | Software Version                        | Of the vehicle                   |
| `target_battery_percentage`                           | Target Battery Percentage               |                                  |

### Last Updated sensor
Provides timestamp when the vehicle has updated own [status information](https://myskoda.readthedocs.io/en/latest/reference/models/status/)
to Skoda servers last time.

This is different from [Last Service Event](#last-service-event).

### Last Operation
The sensor provides the status of the last performed operation. Possible values are "In Progress", "Completed succesfully",
"Completed with warning" or "Error". The sensor changes the value in response to operations requests like charging start/stop,
heating requests, lock/unlock, etc.

The attributes of the sensor contain also additional information like operation name and timestamp.
The previous event information is provided as "history" attribute.

### Last Service Event
The sensor provides the timestamp of the last service event that has been reported by the vehicle. Following service events are monitored:
- change-access
- change-charge-mode
- change-lights
- change-remaining-time
- change-soc
- charging-completed
- charging-status-changed
- climatisation-completed
- departure-ready
- departure-status-changed

The attributes of the sensor contain additional information about the service event (name, timestamp) as well as previously received
event in "history".

NOTE: not all vehicles report all service events.

## Binary Sensors

| Key                       | Name               | Notes |
|---------------------------|--------------------|-------|
| `charger_connected`       | Charger Connected  |       |
| `charger_locked`          | Charge Lock        |       |
| `locked`                  | Vehicle Locked     |       |
| `doors_locked`            | Doors Locked       |       |
| `doors_open`              | Doors Open         |       |
| `windows_open`            | Windows            |       |
| `trunk_open`              | Trunk              |       |
| `bonnet_open`             | Bonnet             |       |
| `sunroof_open`            | Sunroof            |       |
| `lights_on`               | Parking Lights     |       |
| `door_open_front_left`    | Door Front Left    |       |
| `door_open_front_right`   | Door Front Right   |       |
| `door_open_rear_left`     | Door Rear Left     |       |
| `door_open_rear_right`    | Door Rear Right    |       |
| `window_open_front_left`  | Window Front Left  |       |
| `window_open_front_right` | Window Front Right |       |
| `window_open_rear_left`   | Window Rear Left   |       |
| `window_open_rear_right`  | Window Rear Right  |       |

## Switches

Switches become temporarily disabled when toggled, until the API operation completes.

| Key                           | Name                       | Notes                                       |
|-------------------------------|----------------------------|---------------------------------------------|
| `window_heating`              | Window Heating             |                                             |
| `charging_switch`             | Charging                   |                                             |
| `battery_care_mode`           | Battery Care               |                                             |
| `reduced_current`             | Reduced Current            |                                             |
| `charging`                    | Charging                   |                                             |
| `auto_unlock_plug`            | Unlock Plug when Charged   |                                             |
| `ac_at_unlock`                | AC when Unlocked           |                                             |
| `ac_without_external_power`   | AC without External Power  |                                             |
| `ac_seat_heating_front_left`  | Left Seat Heating with AC  |                                             |
| `ac_seat_heating_front_right` | Right Seat Heating with AC |                                             |
| `ac_window_heating`           | Window Heating with AC     |                                             |
| `departure_timer_1`           | Departure Timer 1          | Timer configuration is stored in attributes |
| `departure_timer_2`           | Departure Timer 2          | Timer configuration is stored in attributes |
| `departure_timer_3`           | Departure Timer 3          | Timer configuration is stored in attributes |
| `ac_timer_1`                  | Air-conditioning Timer 1   | Timer configuration is stored in attributes |
| `ac_timer_2`                  | Air-conditioning Timer 2   | Timer configuration is stored in attributes |
| `ac_timer_3`                  | Air-conditioning Timer 3   | Timer configuration is stored in attributes |

## Buttons

Buttons become temporarily disabled when pressed, until the API operation completes.

| Key          | Name           | Notes                         |
|--------------|----------------|-------------------------------|
| `honk_flash` | Honk and Flash |                               |
| `flash`      | Flash          |                               |
| `wakeup`     | Wake Up Car    | :warning: Disabled by default |

### Wake Up Car

This button will result in a wake-up request being sent directly to the car. In order to protect the 12V battery most models have a strict limit on the number of times this can occur before requiring the car to be started. **USE WITH CARE!**

## Climate

Climates use assumed state when modified.

| Key                | Name             | Notes |
|--------------------|------------------|-------|
| `climate`          | Air Conditioning |       |
| `auxiliary_heater` | Auxiliary Heater |       |

## Numbers

Numbers become temporarily disabled when modified, until the API operation completes.

| Key                         | Name            | Notes                           |
|-----------------------------|-----------------|---------------------------------|
| `charge_limit`              | Charge Limit    | In % [50-100] in steps of 10    |
| `auxiliary_heater_duration` | Heater Duration | In minutes [5-60] in steps of 5 |

## Device Tracker

| Key                    | Name         | Notes                        |
|------------------------|--------------|------------------------------|
| `<VIN>_device_tracker` | Charge Limit | In % [50-100] in steps of 10 |

Location of vehicles are exposed as device trackers. While the vehicle is moving the Skoda API does not return GPS coordinates and the device tracker will report the location `vehicle_in_motion`.

### Main Render of Vehicle

The sensor contains the vehicle image as provided by Skoda. This can be used in Home Assistant in different cards, for example:

```
type: picture
image_entity: image.skoda_enyaq_main_render_of_vehicle
```

Besides, there is a set of attributes of the sensor that contains other images provided by the Skoda servers. Example of a templated sensor for an image:

```
- image:
    - name: "Skoda exterior image front"
      url: >
        {{ states.image.skoda_enyaq_main_render_of_vehicle.attributes.composite_renders.charging_light[0].exterior_front }}
```

### Car Info

Sometimes you might need to access a VIN quickly and it might be convenient to use the [Search](https://www.home-assistant.io/integrations/search/) to obtain this data quickly.

To achieve this, you can create a template sensor that prints this data using any entity identifier assigned to your car.

```
{{ device_attr(device_id('sensor.skoda_enyaq_mileage'), 'serial_number') }}
```
