[![Version](https://img.shields.io/github/v/release/skodaconnect/homeassistant-myskoda)](https://github.com/skodaconnect/homeassistant-myskoda/releases)
![Downloads](https://img.shields.io/github/downloads/skodaconnect/homeassistant-myskoda/total)
![Contributors](https://img.shields.io/github/contributors/skodaconnect/homeassistant-myskoda)
[![Translation](https://badges.crowdin.net/homeassistant-myskoda/localized.svg)](https://crowdin.com/project/homeassistant-myskoda/invite?h=1c4f8152c707b666f570b9cb68678ece2227331)

# Home Assistant MySkoda Integration :house_with_garden: :satellite: :car:

A [Home Assistant](https://www.home-assistant.io/) integration for Skoda vehicles based on the official MySkoda App.

- [Getting Started](#getting-started)
  - [Installation](#installation)
  - [Configuration](#configuration)
- [Documentation](#documentation)
  - [Limitations](#limitations)
  - [Additional Configuration](#additional-configuration)
  - [Available Entities](#available-entities)
  - [Operations](#operations)
  - [New Vehicles](#new-vehicles)
  - [Configuration](#configuration-1)
  - [Debugging](#debugging)
  - [Customize polling interval](#customize-polling-interval)
  - [Disabling polling](#disabling-polling)
  - [S-PIN](#s-pin)
  - [Read-only mode](#read-only-mode)
  - [Inner workings](#inner-workings)
- [FAQ](#faq)
- [Contributing](#contributing)
  - [Translations](#translations)
- [Disclaimer](#disclaimer)

## Getting Started

### Installation
You can manually install this integration as an custom_component under Home Assistant or install it using [HACS](https://hacs.xyz/) (recommended).

After installation you will need to restart your HomeAssistant before you can add use it.

#### HACS installation
New to HACS? Start with the [HACS documentation](https://hacs.xyz/docs/use/) first.

1. Go to **HACS > Integrations**
2. Click the **"+"** button in the bottom right
3. Search for **"MySkoda"**
4. Click **Download** and **restart** Home Assistant

#### Manual installation
1. **Download** the `myskoda` repository or folder.
2. **Copy** the `custom_components/myskoda` folder from the downloaded files.
3. **Paste** the `myskoda` folder into your Home Assistant's custom components directory:
   - Path: `<home_assistant_folder>/custom_components/myskoda`
4. **Restart** Home Assistant.

### Configuration
After installing the integration you still need to configure it:

1. Go to `Settings` :arrow_right: `Devices & services`
2. Click `Add Integration` and search for `MySkoda`
3. Enter your MySkoda App login credentials

## Documentation

### Limitations
This integration interacts with the Skoda API in the same way the official MySkoda App does. Consequently if something isn't available in the App, it is very unlikely it will be possible to implement in the integration. Keep this in mind when raising feature requests.

### Additional Configuration

### Available Entities
- The integration will automatically set up various entities depending on the vehicle model and the 'capabilities' reported by the API. For example the adblue sensor should only be created for vehicles with adblue.
- The ID of entities is always constructed as `<entity_type>.<vehicle_model>_<entity_key>`. For example the ID of the Mileage sensor on a Skoda Enyaq would be `sensor.skoda_enyaq_mileage`
- The name of entities depends on your local Home Assistant language.

Refer to [docs/entities.md](docs/entities.md) for the full list of all entities created by the integration.

### Operations

#### Entities becoming temporarily unavailable (Switches, Buttons and Numbers)
When making a change which results in an operation being sent to the car (via the Skoda API), for example when toggling a switch, **the entity will become unavailable until the request completes**.

This prevents overlapping requests from being sent and provides a visual indication that there is an ongoing operation for a given entity.

This happens independently for each entity.

#### Entities using assumed state (Climate)
When making a change in these entities (e.g. changing the target temperature) the entity will remain available and show the new value immediately **even if the value isn't applied in the API and car yet**. This uses the [assumed state](https://www.home-assistant.io/blog/2016/02/12/classifying-the-internet-of-things/#classifiers) entity classifier.

### New Vehicles
If you become the owner of an additional vehicle and that gets added to the same MySkoda account: Congrats!
In order for the integration to discover this new vehicle, you will need to reload the integration or restart HomeAssistant

### Configuration
After installation but before first initialization the integration requests the configuration parameters.
The configuration includes:
- login and password for the account that will control the vehicle (can be same as in MySkoda application)
- polling interval in minutes, see [Customize polling interval](#customize-polling-interval)
- S-PIN, the pin is required for certain operations to be performed, see [S-PIN](#s-pin) section for details

The configuration parameters (except login and password) are available for modification after initialization
from Integrations > MySkoda > Hubs > Select your account > Configure. The change of configuration will trigger
the reload of the integration.

### Debugging

#### Enable debug logging
For comprehensive debug logging you can add this to your `<config dir>/configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    myskoda: debug
    myskoda.mqtt: debug
    myskoda.rest_api: debug
    custom_components.myskoda: debug
    custom_components.myskoda.climate: debug
    custom_components.myskoda.lock: debug
    custom_components.myskoda.device_tracker: debug
    custom_components.myskoda.switch: debug
    custom_components.myskoda.binary_sensor: debug
    custom_components.myskoda.sensor: debug
    custom_components.myskoda.number: debug
    custom_components.myskoda.image: debug
 ```

Pick any of the subjects from the example. If you want to enable full debugging, you only need **myskoda** and **custom_components.myskoda**.

- **myskoda:** Set the debug level for the MySkoda library. This handles all the communication with MySkoda.

- **myskoda.mqtt:** Set the debug level for the MQTT class of the MySkoda library. This handles the push-messages sent from MySkoda to the integration, notifying of changes to/in the car.

- **myskoda.rest_api:** Set the debug level for the REST API of the MySkoda library. This handles all the pull-messages the integration fetches from MySkoda.

- **custom_components.myskoda:** Set debug level for the custom component. The communication between hass and library.

- **custom_components.myskoda.XYZ** Sets debug level for individual entity types in the custom component.

#### Enable tracing
Enabling tracing makes the integration log the complete interactions between the MySkoda servers and HomeAssistant. This will contain personal sensitive information.
You can enable tracing by going to Integrations > MySkoda > Hubs > Select your account > Configure

Choose "API response tracing"

Alternately, click the button below, select your account, click Configure
[![Button](https://my.home-assistant.io/badges/integration.svg)](https://my.home-assistant.io/redirect/integration/?domain=myskoda)

#### Diagnostics
The **Diagnostics** feature allows you to directly download diagnostic data for sharing in issue reports. Providing diagnostics data when reporting an issue helps developers diagnose and resolve your problem more efficiently.

You can download the diagnostics data as a text file from the device page or the integrations dashboard.

Diagnostics file include:

- Home Assistant version and details
- List of installed components and their versions
- MySkoda integration version and details
- Anonymized vehicle fixtures from the MySkoda API. (fixtures can be found under the `data` key in the diagnostics response)

> **Note:** Vehicle fixtures are responses from all available MySkoda API endpoints always returned in both raw and serialized format.

### Customize polling interval
This integration does not poll at a set interval, instead when the last update has been a while, we request new information from MySkoda.
The reason for this is that cars emit a lot of events when they are operating, and we use these events to partially update the car information.

When the car is quiet for a period we call the **POLLING INTERVAL**, we will request a full update of the car.

By default, this POLLING INTERVAL is set to 30 minutes. You can tune this to anything between 1 and 1440 minutes (1 day) by filling in the desired value in
Integrations > MySkoda > Hubs > Select your account > Configure

Alternately, click the button below, select your account, click Configure
[![Button](https://my.home-assistant.io/badges/integration.svg)](https://my.home-assistant.io/redirect/integration/?domain=myskoda)

### Disabling polling
You can disable polling completely and use automations to update the data from MySkoda. This is done in two steps:

1. Disable polling in the integration:
- Open the integration settings in your HomeAssistant. If you have HomeAssistant Cloud, click the button.
[![Button](https://my.home-assistant.io/badges/integration.svg)](https://my.home-assistant.io/redirect/integration/?domain=myskoda)
- Select the three dots behind the desired account to edit.
- Select System Settings
- Disable Polling (the second option)
- Click save

2. Call the following action in an automation, updating the `entity_id` to suit your vehicle(s):

```yaml
action: homeassistant.update_entity
target:
  entity_id: device_tracker.skoda_enyaq_position
data:
  entity_id:
    - device_tracker.skoda_enyaq_position
```

### S-PIN
For some operations, such as locking and unlocking doors, it is required to fill in the S-PIN that you have set for privileged access to your car via the App. This integration does not support setting the S-PIN yet.
Fill in the required S-PIN in Settings > Integrations > MySkoda > Configuration > S-PIN and after a few seconds you will have the options available in HomeAssistant.

### Read-only mode
The opposite to S-PIN is read-only mode. In this mode, all buttons, switches and other functionality that allows you to change settings remotely are disabled.
In order not to accidentally delete data, we do not delete the entities.

Also, if you disable read-only mode, the buttons, switches, etc will become available again.

### Inner workings
Refer to [docs/design.md](docs/design.md).

## FAQ

#### Is there a sensor to indicate the vehicle is moving?
There is not but the device tracker will report `vehicle_in_motion`. If you need a binary sensor you can create a [template sensor](https://www.home-assistant.io/integrations/template/). Example:

```python
{% if states('device_tracker.skoda_enyaq_position') == 'vehicle_in_motion' %}
True
{% endif %}
```

#### Why does toggling a switch make it unavailable?
See [Operations](#operations-switches-buttons-and-numbers).

#### Can I have the entities report values in miles instead of kilometers?

Yes. The Skoda API reports all values in metric and this is also how the data is used by the integration and stored in Home Assistant.

Home Assistant can convert the values by configurating the _Unit system_ in the [General Settings](https://www.home-assistant.io/docs/configuration/basic/).

## Contributing
This integration and the associated [Python library](https://github.com/skodaconnect/myskoda) is maintained by a small number of people. Maintainers also tend to come and go when they no longer own a Skoda car :sweat_smile:.

Contributions are very welcomed, both as issues, but even more so as pull requests!

Please [join our Discord](https://discord.gg/t7az2hSJXq) and help development by providing feedback and details about the vehicles you are using.

### Translations
You can help us translate your MySkoda integration into your language!
Just [join our Crowdin project](https://crowdin.com/project/homeassistant-myskoda/invite?h=1c4f8152c707b666f570b9cb68678ece2227331).
If your desired language is not available, please [open an issue](https://github.com/skodaconnect/homeassistant-myskoda/issues/new/choose) and let us know about it!

## Disclaimer
This Homeassistant integration uses an unofficial API client for the Skoda API and is not affiliated with, endorsed by, or associated with Skoda Auto or any of its subsidiaries.

Use this project at your own risk. Skoda Auto may update or modify its API without notice, which could render this integration inoperative or non-compliant. The maintainers of this project are not responsible for any misuse, legal implications, or damages arising from its use.

Ensure compliance with Skoda Auto's terms of service and any applicable laws when using this software.
