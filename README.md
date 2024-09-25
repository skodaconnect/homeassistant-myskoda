# MySkoda Integration for Skoda vehicles compatible with MySkoda-App.

MySkoda integration using the API that the MySkoda App uses.

## Status: This project is a new implementation of a relatively new API. Consider this code alpha. 

Contributions are welcomed, both as issues, but more as pull requests :) 

## Capabilities

### Sensors 

- Software Version
- Battery Percentage
- Charging Power
- Remaining Distance
- Target Battery Percentage
- Milage
- Charge Type
- Charging State
- Remaining Charging Time
- Last Updated

### Binary Sensors

- Charger Connected
- Charger Locked
- Everything Locked
- Doors Locked
- Doors Open
- Windows Open
- Trunk Open
- Bonnet Open
- Lights On

### Switches

- Window Heating
- Reduced Current
- Battery Care Mode

### Climate

Air conditioning is exposed as climate.

### Numbers

- Charging Limit

### Device Tracker

Location of vehicles are exposed as device trackers.

## Further Resources

Check out the [awesome work from the team behind pyskodaconnect](https://github.com/skodaconnect/homeassistant-skodaconnect).

Sadly, the integration is currently not working with new cars that can no longer access the old Skoda Essentials App. This is a rewrite to the new MySkoda API.
