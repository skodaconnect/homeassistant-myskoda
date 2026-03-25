# Home Assistant Entities

## Sensors

| Key                                                   | Name                                       | Unit       | Capability required               | Notes                                      |
|-------------------------------------------------------|--------------------------------------------|------------|-----------------------------------|--------------------------------------------|
| `adblue_range`                                        | AdBlue Range                               | km         | STATE, FUEL_STATUS                | Not shown for electric vehicles            |
| `aux_estimated_time_left_to_reach_target_temperature` | Heater Time to reach target temperature    | min        | AUXILIARY_HEATING                 |                                            |
| `battery_percentage`                                  | Battery Percentage                         | %          | CHARGING                          | Dynamic icon tracks charge level           |
| `car_captured`                                        | Last Updated                               | timestamp  | STATE                             | See [Last Updated sensor](#last-updated-sensor) |
| `charge_type`                                         | Charge Type                                |            | CHARGING                          | AC, DC                                     |
| `charging_power`                                      | Charging Power                             | kW         | CHARGING, EXTENDED_CHARGING_SETTINGS |                                         |
| `charging_rate`                                       | Charging Rate                              | km/h       | CHARGING, EXTENDED_CHARGING_SETTINGS | Range added per hour of charging        |
| `charging_state`                                      | Charging State                             |            | CHARGING                          | Ready, Charging, Conserving, ...           |
| `combustion_range`                                    | Combustion Range                           | km         | STATE, FUEL_STATUS                | Hybrid vehicles only                       |
| `electric_range`                                      | Electric Range                             | km         | STATE, FUEL_STATUS, CHARGING_MQB  | Hybrid (MQB) vehicles only                 |
| `estimated_time_left_to_reach_target_temperature`     | AC Time to reach target temperature        | min        | AIR_CONDITIONING                  |                                            |
| `fuel_level`                                          | Fuel Level                                 | %          | STATE, FUEL_STATUS                |                                            |
| `gas_level`                                           | Gas Level                                  | %          | STATE, FUEL_STATUS                | CNG hybrid vehicles only                   |
| `gas_range`                                           | Gas Range                                  | km         | STATE, FUEL_STATUS                | CNG hybrid vehicles only                   |
| `inspection`                                          | Next Inspection                            | days       |                                   |                                            |
| `inspection_in_km`                                    | Next Inspection                            | km         |                                   |                                            |
| `last_trip_average_fuel_consumption`                  | Last Trip Average Fuel Consumption         | l/100km    | TRIP_STATISTICS                   | Diagnostic category                        |
| `last_trip_average_speed`                             | Last Trip Average Speed                    | km/h       | TRIP_STATISTICS                   | Diagnostic category                        |
| `last_trip_mileage`                                   | Last Trip Mileage                          | km         | TRIP_STATISTICS                   | Diagnostic category                        |
| `last_trip_travel_time`                               | Last Trip Travel Time                      | min        | TRIP_STATISTICS                   | Diagnostic category                        |
| `milage`                                              | Mileage                                    | km         |                                   | Monotonically increasing; API glitch-protected |
| `oil_service_in_days`                                 | Oil Service                                | days       | FUEL_STATUS                       |                                            |
| `oil_service_in_km`                                   | Oil Service                                | km         | FUEL_STATUS                       |                                            |
| `operation`                                           | Last Operation                             |            |                                   | Diagnostic category. See [Last Operation](#last-operation) |
| `outside_temperature`                                 | Outside Temperature                        | °C         | OUTSIDE_TEMPERATURE               |                                            |
| `overall_average_electric_consumption`                | Overall Average Electric Consumption       | kWh/100km  | TRIP_STATISTICS                   | Diagnostic category                        |
| `overall_average_fuel_consumption`                    | Overall Average Fuel Consumption           | l/100km    | TRIP_STATISTICS                   | Diagnostic category                        |
| `overall_average_speed`                               | Overall Average Speed                      | km/h       | TRIP_STATISTICS                   | Diagnostic category                        |
| `overall_mileage`                                     | Overall Mileage                            | km         | TRIP_STATISTICS                   | Diagnostic category                        |
| `overall_travel_time`                                 | Overall Travel Time                        | min        | TRIP_STATISTICS                   | Diagnostic category                        |
| `range`                                               | Range                                      | km         | STATE                             | Total estimated range                      |
| `remaining_charging_time`                             | Remaining Charging Time                    | min        | CHARGING                          |                                            |
| `service_event`                                       | Last Service Event                         | timestamp  |                                   | Diagnostic category. See [Last Service Event](#last-service-event) |
| `software_version`                                    | Software Version                           |            | CHARGING_MEB                      | Diagnostic category                        |
| `target_battery_percentage`                           | Target Battery Percentage                  | %          | CHARGING, EXTENDED_CHARGING_SETTINGS |                                         |

### Last Updated sensor
Provides timestamp when the vehicle has last pushed its [status information](https://myskoda.readthedocs.io/en/latest/reference/models/status/) to Skoda servers.

This is different from [Last Service Event](#last-service-event).

### Last Operation
The sensor provides the status of the last performed operation. Possible values are `in_progress`, `completed_success`, `completed_warning`, or `error`. The sensor updates in response to operation requests such as charging start/stop, heating, lock/unlock, etc.

Attributes include the operation name, request ID, error code, and timestamp. Previous operation information is available via the `history` attribute.

### Last Service Event
The sensor provides the timestamp of the last service event reported by the vehicle. The following service events are monitored:
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

Attributes include event name, timestamp, and additional event data. The previous event is available via the `history` attribute.

> **Note:** Not all vehicles report all service events.

---

## Binary Sensors

| Key                       | Name               | Device class | Capability required | Notes                                         |
|---------------------------|--------------------|--------------|---------------------|-----------------------------------------------|
| `bonnet_open`             | Bonnet             | opening      | STATE               |                                               |
| `charger_connected`       | Charger Connected  | plug         | AIR_CONDITIONING    |                                               |
| `charger_lock`            | Charge Lock        | lock         | AIR_CONDITIONING    | `on` = unlocked (can be unplugged)            |
| `doors_lock`              | Doors Locked       | lock         | STATE               | `on` = unlocked                               |
| `doors_open`              | Doors Open         | door         | STATE               |                                               |
| `door_open_front_left`    | Door Front Left    | door         | STATE               |                                               |
| `door_open_front_right`   | Door Front Right   | door         | STATE               |                                               |
| `door_open_rear_left`     | Door Rear Left     | door         | STATE               |                                               |
| `door_open_rear_right`    | Door Rear Right    | door         | STATE               |                                               |
| `lights_on`               | Parking Lights     | light        | STATE               |                                               |
| `sunroof_open`            | Sunroof            | opening      | STATE               | Unavailable if vehicle has no sunroof         |
| `trunk_open`              | Trunk              | opening      | STATE               |                                               |
| `vehicle_battery_protection` | Battery Protection | running   | READINESS           |                                               |
| `vehicle_in_motion`       | In motion          | motion       | READINESS           |                                               |
| `vehicle_lock`            | Vehicle Locked     | lock         | STATE               | `on` = unlocked                               |
| `vehicle_reachable`       | Reachable          | connectivity | READINESS           | Diagnostic category                           |
| `window_open_front_left`  | Window Front Left  | window       | STATE               |                                               |
| `window_open_front_right` | Window Front Right | window       | STATE               |                                               |
| `window_open_rear_left`   | Window Rear Left   | window       | STATE               |                                               |
| `window_open_rear_right`  | Window Rear Right  | window       | STATE               |                                               |
| `windows_open`            | Windows            | window       | STATE               |                                               |

---

## Switches

Switches become temporarily unavailable when toggled, until the API operation completes.

Config-category switches (`battery_care_mode`, `reduced_current`, `auto_unlock_plug`, `ac_at_unlock`, `ac_without_external_power`, seat/window heating with AC, and all timer switches) are in the **Config** entity category and may be hidden by default in some HA views.

| Key                           | Name                       | Capability required                    | Notes                                       |
|-------------------------------|----------------------------|----------------------------------------|---------------------------------------------|
| `ac_at_unlock`                | AC when Unlocked           | AIR_CONDITIONING_SMART_SETTINGS        | Config category                             |
| `ac_seat_heating_front_left`  | Left Seat Heating with AC  | AIR_CONDITIONING_SMART_SETTINGS        | Config category                             |
| `ac_seat_heating_front_right` | Right Seat Heating with AC | AIR_CONDITIONING_SMART_SETTINGS        | Config category                             |
| `ac_timer_1`                  | Air-conditioning Timer 1   | AIR_CONDITIONING_TIMERS                | Config category. Timer config in attributes |
| `ac_timer_2`                  | Air-conditioning Timer 2   | AIR_CONDITIONING_TIMERS                | Config category. Timer config in attributes |
| `ac_timer_3`                  | Air-conditioning Timer 3   | AIR_CONDITIONING_TIMERS                | Config category. Timer config in attributes |
| `ac_window_heating`           | Window Heating with AC     | AIR_CONDITIONING_SMART_SETTINGS        | Config category                             |
| `ac_without_external_power`   | AC without External Power  | AIR_CONDITIONING_HEATING_SOURCE_ELECTRIC | Config category                           |
| `auto_unlock_plug`            | Unlock Plug when Charged   | CHARGING, EXTENDED_CHARGING_SETTINGS   | Config category                             |
| `battery_care_mode`           | Battery Care               | BATTERY_CHARGING_CARE                  | Config category                             |
| `charging`                    | Charging                   | CHARGING                               | Start/stop charging session                 |
| `departure_timer_1`           | Departure Timer 1          | DEPARTURE_TIMERS                       | Config category. Timer config in attributes |
| `departure_timer_2`           | Departure Timer 2          | DEPARTURE_TIMERS                       | Config category. Timer config in attributes |
| `departure_timer_3`           | Departure Timer 3          | DEPARTURE_TIMERS                       | Config category. Timer config in attributes |
| `reduced_current`             | Reduced Current            | CHARGING                               | Config category                             |
| `window_heating`              | Window Heating             | WINDOW_HEATING                         |                                             |

---

## Buttons

Buttons become temporarily unavailable when pressed, until the API operation completes. All buttons are disabled in read-only mode.

| Key          | Name           | Capability required | Notes                              |
|--------------|----------------|---------------------|------------------------------------|
| `flash`      | Flash          | HONK_AND_FLASH      |                                    |
| `honk_flash` | Honk and Flash | HONK_AND_FLASH      |                                    |
| `wakeup`     | Wake Up Car    | (none)              | Disabled by default. See warning below. |

### Wake Up Car

This button sends a wake-up request directly to the car. Most models have a strict limit on the number of wake-ups allowed before the car must be started, to protect the 12V battery. **USE WITH CARE.**

---

## Climate

Climate entities use assumed state — changes appear immediately in Home Assistant even before the API confirms them.

| Key                | Name             | Capability required  | Notes |
|--------------------|------------------|----------------------|-------|
| `auxiliary_heater` | Auxiliary Heater | AUXILIARY_HEATING    |       |
| `climate`          | Air Conditioning | AIR_CONDITIONING     |       |

---

## Numbers

Number entities become temporarily unavailable when modified, until the API operation completes. Both entities are in the **Config** entity category.

| Key                         | Name            | Unit | Range      | Step | Capability required   | Notes |
|-----------------------------|-----------------|------|------------|------|-----------------------|-------|
| `auxiliary_heater_duration` | Heater Duration | min  | 5–60       | 5    | AUXILIARY_HEATING     | State is restored across restarts. Not available if AUXILIARY_HEATING_TEMPERATURE_SETTING is present |
| `charge_limit`              | Charge Limit    | %    | 50–100     | 10   | EXTENDED_CHARGING_SETTINGS or CHARGING (non-MQB) | Config category |

---

## Device Tracker

| Key              | Name     | Capability required | Notes                                                      |
|------------------|----------|---------------------|------------------------------------------------------------|
| `device_tracker` | Position | PARKING_POSITION    | Reports `vehicle_in_motion` state while the vehicle is moving |

Location is exposed as a device tracker. While the vehicle is moving the Skoda API does not return GPS coordinates; the tracker will report the `vehicle_in_motion` state instead of a location.

---

## Images

| Key                  | Name                        | Notes                                                    |
|----------------------|-----------------------------|----------------------------------------------------------|
| `render_vehicle_main` | Main Render of Vehicle      | Diagnostic category. See [Main Render](#main-render-of-vehicle) |
| `render_light_3x`    | Light Status Render of Vehicle | Disabled by default. Updated when vehicle status changes |

### Main Render of Vehicle

The image entity contains the vehicle image as provided by Skoda. It can be used in Home Assistant cards, for example:

```yaml
type: picture
image_entity: image.skoda_enyaq_main_render_of_vehicle
```

The entity also exposes additional render URLs as attributes. Example template sensor for a specific composite render:

```yaml
- image:
    - name: "Skoda exterior image front"
      url: >
        {{ states.image.skoda_enyaq_main_render_of_vehicle.attributes.composite_renders.charging_light[0].exterior_front }}
```

---

## Car Info

To retrieve the VIN quickly using a template sensor:

```yaml
{{ device_attr(device_id('sensor.skoda_enyaq_mileage'), 'serial_number') }}
```
