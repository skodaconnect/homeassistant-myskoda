![Version](https://img.shields.io/github/v/release/skodaconnect/homeassistant-myskoda)
![Downloads](https://img.shields.io/github/downloads/skodaconnect/homeassistant-myskoda/total)
![Contributors](https://img.shields.io/github/contributors/skodaconnect/homeassistant-myskoda)
![Translation](https://badges.crowdin.net/homeassistant-myskoda/localized.svg)

# MySkoda Integration for Skoda vehicles compatible with MySkoda-App.

MySkoda integration using the API that the MySkoda App uses.

**Status:** This project is a new implementation of a relatively new API. Consider this code alpha. 

Contributions are welcomed, both as issues, but more as pull requests :) 

Please [join our Discord](https://discord.gg/t7az2hSJXq) and help development by providing feedback and details about the vehicles you are using.

## Translations

You can help us translate your MySkoda integration into your language!
Just [join our Crowdin project](https://crowdin.com/project/homeassistant-myskoda/invite?h=1c4f8152c707b666f570b9cb68678ece2227331)

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
- Maintenance Interval

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

## Sending updates

To make sure updates end up in the car the way intended by the you, we throttle all equal changes to the car for 30s.
Simply put: You can change a setting in the car once every 30s, but you can change multiple settings in sequence.

So:
- If you change the seat-heating to on, you can immediately change the window-heating to on as well.
- If you change the seat-heating to on, you cannot turn it back off again for 30s

The requests will silently be ignored by HomeAssistant, so make sure you wait at least 30s before sending another request
