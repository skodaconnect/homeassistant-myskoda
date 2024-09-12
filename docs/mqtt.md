# MQTT Protocol

This is a specification for the MQTT protocol that the server uses to communicate with the app.

[[TOC]]

## Connection

**Host:**

- `3.72.252.203`
- `3.73.186.137`

**Port:** 8883
**Username:** Doesn't matter, but the app uses `2940a48-3881-43c2-be46-c4cf53e7fc7b`
**Password:** Your standard JWT Authorization Token, same as used to login with the app.

## Message structure

### /operation-request

These messages describe how the car reacts to requests by the app.
For example, if a `start-stop-air-conditioning` message is sent, the MQTT server will first answer with a `IN_PROGRESS` and then a `COMPLETED_SUCCESS` message.

#### Common Fields

| Field         | Description                                                            | Example                                  |
| ------------- | ---------------------------------------------------------------------- | ---------------------------------------- |
| **version**   | Protocol version.                                                      | `1`                                      |
| **traceId**   | This id stays the same across a request. Unsure what this is used for. | `"7620dfdabcf14fc5a3c832dccfb2510a"`     |
| **requestId** | This id stays the same across a request. Unsure what this is used for. | `"df538725-66ff-4644-9a5d-7f3eac8838fb"` |
| **operation** | Timestamp from when the message originated in ISO format.              | `"start-flash"`                          |
| **status**    | Probably the origin of the message.                                    | `"IN_PROGRESS"`                          |
| **errorCode** | Only present in error messages. Describes the type of error.           | `timeout`                                |

### /service-event

These messages are sent proactively from the vehicle, or somewhat periodically by some other participant that is not the app.

#### Common Fields

The following fields are present in every entity returned from the `/service-event` topic:

| Field           | Description                                                            | Example                                  |
| --------------- | ---------------------------------------------------------------------- | ---------------------------------------- |
| **version**     | Protocol version.                                                      | `1`                                      |
| **traceId**     | This id stays the same across a request. Unsure what this is used for. | `"c94de7d5a966c79c7666328b005b55ee"`     |
| **timestamp**   | Timestamp from when the message originated in ISO format.              | `2024-09-09T20:34:53.546Z`               |
| **producer**    | Probably the origin of the message.                                    | `SKODA_MHUB`                             |
| **name**        | Name of the event.                                                     | `"change-soc"`                           |
| **data.userId** | User id.                                                               | `"50f8b18c-d444-422c-998f-2b599f4f0ec7"` |
| **data.vin**    | Vehicle identification number.                                         | `"TMBJB9NY6RF999999"`                    |

## Subjects

The app subscribes to the following topics:

### Generic

- `{user_id}/{vin}/account-event/privacy`
- `{user_id}/{vin}/operation-request/charging/update-battery-support`
- `{user_id}/{vin}/operation-request/vehicle-access/lock-vehicle`
- `{user_id}/{vin}/operation-request/vehicle-wakeup/wakeup`
- `{user_id}/{vin}/service-event/vehicle-status/access`
- `{user_id}/{vin}/service-event/vehicle-status/lights`

### Enyaq 2024

- `{user_id}/{vin}/operation-request/air-conditioning/set-target-temperature`
- `{user_id}/{vin}/operation-request/air-conditioning/start-stop-air-conditioning`
- `{user_id}/{vin}/operation-request/air-conditioning/start-stop-window-heating`
- `{user_id}/{vin}/operation-request/charging/start-stop-charging`
- `{user_id}/{vin}/operation-request/vehicle-services-backup/apply-backup`
- `{user_id}/{vin}/service-event/air-conditioning`
- `{user_id}/{vin}/service-event/charging`

### Octavia 3 2019

- `{user_id}/{vin}/operation-request/vehicle-access/honk-and-flash`
- `{user_id}/{vin}/operation-request/vehicle-services-backup/apply-backup`

### /operation-request/air-conditioning/set-target-temperature

Published when the user requests that the temperature of the air conditioning is changed:

#### Operations

- `set-air-conditioning-target-temperature`

#### Example Messages

```json
{
  "version": 1,
  "operation": "set-air-conditioning-target-temperature",
  "status": "IN_PROGRESS",
  "traceId": "c94de7d5a966c79c7666328b005b55ee",
  "requestId": "e8f6fd16-d6c1-44fa-8b5e-2c7ddaae2cc2"
}
```

### /operation-request/air-conditioning/start-stop-air-conditioning

Published when air conditioning is started or stopped and also when it is completed.
Will report the status of the request while it is running.

#### Operations

- `stop-air-conditioning`
- `start-air-conditioning`

#### Example Messages

```json
{
  "version": 1,
  "operation": "stop-air-conditioning",
  "status": "IN_PROGRESS",
  "traceId": "e063a0da2c324315b8f04477340dd4b1",
  "requestId": "df538725-66ff-4644-9a5d-7f3eac8838fb"
}
```

```json
{
  "version": 1,
  "operation": "start-air-conditioning",
  "status": "COMPLETED_SUCCESS",
  "traceId": "9ec9816ef8924036a32dfb8285192b31",
  "requestId": "b0327db0-52a8-4822-8318-1411d237c707"
}
```

### /operation-request/air-conditioning/start-stop-window-heating

Updated when window heating is started, stopped or completed.

#### Operations

- `stop-window-heating`
- `start-window-heating`

#### Example Messages

```json
{
  "version": 1,
  "operation": "start-window-heating",
  "status": "IN_PROGRESS",
  "traceId": "800a74737b5a4328862d958c35b71b74",
  "requestId": "5a16b265-85e7-4502-bd24-c92091c3df31"
}
```

```json
{
  "version": 1,
  "operation": "start-window-heating",
  "status": "ERROR",
  "errorCode": "timeout",
  "traceId": "800a74737b5a4328862d958c35b71b74",
  "requestId": "5a16b265-85e7-4502-bd24-c92091c3df31"
}
```

### /operation-request/charging/start-stop-charging

Updated when the charging is started or stopped via the app (not when it is stopped due to unplugged cable, etc.).

#### Operations

- `start-charging`
- `stop-charging`

#### Example Messages

```json
{
  "version": 1,
  "operation": "start-charging",
  "status": "IN_PROGRESS",
  "traceId": "036b76283bed18a1fe34fb319c21d2e0",
  "requestId": "76908f3f-e0f1-47a7-9541-c40a52ca8e4b"
}
```

### /operation-request/vehicle-access/honk-and-flash

Updated when the user requested the car to flash or honk and flash via the app.

#### Operations

- `start-flash`
- `start-honk`

#### Example Messages

```json
{
  "version": 1,
  "operation": "start-flash",
  "status": "IN_PROGRESS",
  "traceId": "7620dfdabcf14fc5a3c832dccfb2510a",
  "requestId": "531f8dc4-8c2e-44ca-ac43-3cf47003d8cc"
}
```

```json
{
  "version": 1,
  "operation": "start-honk",
  "status": "COMPLETED_SUCCESS",
  "traceId": "2f546702916813538dce19ace9f6dac4",
  "requestId": "48335d5d-7f82-482c-868a-3dc1bbf6e227"
}
```

### /service-event/charging

Published to while the car is charging.

**Name:** `"change-soc"`

#### Special fields

| Field                 | Description                                                                        | Example      |
| --------------------- | ---------------------------------------------------------------------------------- | ------------ |
| **data.mode**         | Unknown. Only known value is `manual`.                                             | `"manual"`   |
| **data.state**        | See documentation for this field below.                                            | `"charging"` |
| **data.soc**          | Current charge of battery in percent, encoded as string.                           | `"77"`       |
| **data.chargedRange** | Estimated distance of the car in km, ecnoded as string.                            | `"207"`      |
| **data.timeToFinish** | Estimation on when the target percentage is reached in minutes, encoded as string. | `"25"`       |

#### Field `data.state`

- `"charging"`: Vehicle is currently charging.
- `"chargePurposeReachedAndNotConservationCharging"`: Vehicle is full and will stop charging.
- `"notReadyForCharging"`: Fired while the vehicle is discharging, e.g. while driving.

#### Example Messages

```json
{
  "version": 1,
  "traceId": "cd2e3695-c136-4835-8e05-7e6fc305e0b2",
  "timestamp": "2024-09-11T21:06:26Z",
  "producer": "SKODA_MHUB",
  "name": "change-soc",
  "data": {
    "mode": "manual",
    "state": "charging",
    "soc": "74",
    "chargedRange": "207",
    "timeToFinish": "25",
    "userId": "50f8b18c-d444-422c-998f-2b599f4f0ec7",
    "vin": "TMBJB9NY6RF999999"
  }
}
```

```json
{
  "version": 1,
  "traceId": "2b76b461-89cd-4a95-ac88-26d66e413241",
  "timestamp": "2024-09-11T21:17:09Z",
  "producer": "SKODA_MHUB",
  "name": "change-soc",
  "data": {
    "mode": "manual",
    "state": "charging",
    "soc": "77",
    "chargedRange": "215",
    "timeToFinish": "15",
    "userId": "50f8b18c-d444-422c-998f-2b599f4f0ec7",
    "vin": "TMBJB9NY6RF999999"
  }
}
```

```json
{
  "version": 1,
  "traceId": "576f65fa-5c81-4b07-b6dd-8ef31957e79b",
  "timestamp": "2024-09-11T21:27:48Z",
  "producer": "SKODA_MHUB",
  "name": "change-soc",
  "data": {
    "mode": "manual",
    "state": "chargePurposeReachedAndNotConservationCharging",
    "soc": "80",
    "chargedRange": "223",
    "timeToFinish": "0",
    "userId": "50f8b18c-d444-422c-998f-2b599f4f0ec7",
    "vin": "TMBJB9NY6RF999999"
  }
}
```

### /service-event/vehicle-status/access

Published whenever anything happens with the car (unlocked, door opened, charger plugged, etc.).
Probably "access" doesn't mean physical access in this context, but rather digital access of the car's capabilities.

**Name:** `"change-access"`

#### Example Messages

```json
{
  "version": 1,
  "traceId": "f9de3b45-9802-470d-ab45-221f4cf8fd97",
  "timestamp": "2024-09-09T20:34:53.546Z",
  "producer": "SKODA_MHUB",
  "name": "change-access",
  "data": {
    "userId": "50f8b18c-d444-422c-998f-2b599f4f0ec7",
    "vin": "TMBJB9NY6RF999999"
  }
}
```

```json
{
  "version": 1,
  "traceId": "f0961cdf-6909-4d62-a073-adb642908363",
  "timestamp": "2024-09-09T20:49:27.564Z",
  "producer": "SKODA_MHUB",
  "name": "change-access",
  "data": {
    "userId": "50f8b18c-d444-422c-998f-2b599f4f0ec7",
    "vin": "TMBJB9NY6RF999999"
  }
}
```

### /service-event/vehicle-status/lights

Published when the lights of the vehicle are turned on or off.

**Name:** `"change-lights"`

#### Example Messages

```json
{
  "version": 1,
  "traceId": "6a9479b6-dc07-4691-9271-120c45b7b109",
  "timestamp": "2024-09-09T20:53:39.560Z",
  "producer": "SKODA_MHUB",
  "name": "change-lights",
  "data": {
    "userId": "50f8b18c-d444-422c-998f-2b599f4f0ec7",
    "vin": "TMBJB9NY6RF999999"
  }
}
```

### /account-event/privacy

### /operation-request/charging/update-battery-support

### /operation-request/vehicle-access/lock-vehicle

### /operation-request/vehicle-services-backup/apply-backup

### /operation-request/vehicle-wakeup/wakeup

### /service-event/air-conditioning
