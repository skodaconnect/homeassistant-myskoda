# MySkoda Integration for Enyaq

MySkoda Enyaq integration using the API that the MySkoda App uses.

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

Sadly, their integration is currently not working with new cars that can no longer access the old Skoda Essentials App. A rewrite to the new MySkoda API is pending.