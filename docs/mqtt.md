## Connection

Host: 3.73.186.137:8883
Username: Doesn't matter, but the app uses `2940a48-3881-43c2-be46-c4cf53e7fc7b`
Password: Your standard JWT Authorization Token

## Message structure

### /operation-request

These messages describe how the car reacts to requests by the app.
For example, if a `start-stop-air-conditioning` message is sent, the MQTT server will first answer with a `IN_PROGRESS` and then a `COMPLETED_SUCCESS` message.

#### Fields

* **version**: Always the number `1`.
* **operation**: The actual operation that has been requested. Example: `stop-air-conditioning`.
* **status**: `"IN_PROGRESS"`, `"COMPLETED_SUCCESS"` or `"ERROR"`
* **traceId**: This id stays the same across a request. Unsure what this is used for.
* **requestId**: This id stays the same across a request.
* **errorCode**: Only present in error messages. Describes the type of error. Example: `timeout`.

### /service-event

These messages are sent proactively from the vehicle, or somewhat periodically by some other participant that is not the app.

#### Fields

* **version**: Always the number `1`.
* **traceId**: This id stays the same across a request. Unsure what this is used for.
* **timestamp**: Timestamp from when the message originated in ISO format. Example: `2024-09-09T20:34:53.546Z`
* **producer**: Probably the origin of the message, only known value is `SKODA_MHUB`
* **name**: Perhaps the type of event?
* **data.userId**: The user's id as received from the HTTP API
* **data.vin**: The VIN

## Subjects

The app subscribes to the following topics:

* `{user_id}/{vin}/operation-request/charging/start-stop-charging`
* `{user_id}/{vin}/operation-request/vehicle-access/lock-vehicle`
* `{user_id}/{vin}/operation-request/air-conditioning/set-target-temperature`
* `{user_id}/{vin}/operation-request/air-conditioning/start-stop-air-conditioning`
* `{user_id}/{vin}/operation-request/air-conditioning/start-stop-window-heating`
* `{user_id}/{vin}/service-event/vehicle-status/access`
* `{user_id}/{vin}/operation-request/charging/update-battery-support`
* `{user_id}/{vin}/account-event/privacy`
* `{user_id}/{vin}/service-event/air-conditioning`
* `{user_id}/{vin}/service-event/charging`
* `{user_id}/{vin}/service-event/vehicle-status/lights`
* `{user_id}/{vin}/operation-request/vehicle-services-backup/apply-backup`
* `{user_id}/{vin}/operation-request/vehicle-wakeup/wakeup`

### /account-event/privacy

### /operation-request/air-conditioning/set-target-temperature

#### Example Messages

```json
{"version":1,"operation":"set-air-conditioning-target-temperature","status":"IN_PROGRESS","traceId":"c94de7d5a966c79c7666328b005b55ee","requestId":"e8f6fd16-d6c1-44fa-8b5e-2c7ddaae2cc2"}
```

### /operation-request/air-conditioning/start-stop-air-conditioning

#### Example Messages

```json
{"version":1,"operation":"stop-air-conditioning","status":"IN_PROGRESS","traceId":"e063a0da2c324315b8f04477340dd4b1","requestId":"df538725-66ff-4644-9a5d-7f3eac8838fb"}
```

```json
{"version":1,"operation":"stop-air-conditioning","status":"COMPLETED_SUCCESS","traceId":"e063a0da2c324315b8f04477340dd4b1","requestId":"df538725-66ff-4644-9a5d-7f3eac8838fb"}
```

### /operation-request/air-conditioning/start-stop-window-heating

#### Example Messages

```json
{"version":1,"operation":"start-window-heating","status":"IN_PROGRESS","traceId":"800a74737b5a4328862d958c35b71b74","requestId":"5a16b265-85e7-4502-bd24-c92091c3df31"}
```

```json
{"version":1,"operation":"start-window-heating","status":"ERROR","errorCode":"timeout","traceId":"800a74737b5a4328862d958c35b71b74","requestId":"5a16b265-85e7-4502-bd24-c92091c3df31"}
```

### /operation-request/charging/start-stop-charging

#### Example Messages

```json
{"version":1,"operation":"start-charging","status":"IN_PROGRESS","traceId":"036b76283bed18a1fe34fb319c21d2e0","requestId":"76908f3f-e0f1-47a7-9541-c40a52ca8e4b"}
```

### /operation-request/charging/update-battery-support

### /operation-request/vehicle-access/lock-vehicle

### /operation-request/vehicle-services-backup/apply-backup

### /operation-request/vehicle-wakeup/wakeup

### /service-event/air-conditioning

### /service-event/charging

### /service-event/vehicle-status/access

#### Example Messages

```json
{"version":1,"traceId":"f9de3b45-9802-470d-ab45-221f4cf8fd97","timestamp":"2024-09-09T20:34:53.546Z","producer":"SKODA_MHUB","name":"change-access","data":{"userId":"userid","vin":"vin"}}
```

```json
{"version":1,"traceId":"f0961cdf-6909-4d62-a073-adb642908363","timestamp":"2024-09-09T20:49:27.564Z","producer":"SKODA_MHUB","name":"change-access","data":{"userId":"userid","vin":"vin"}}
```

### /service-event/vehicle-status/lights

#### Example Messages

```json
{"version":1,"traceId":"6a9479b6-dc07-4691-9271-120c45b7b109","timestamp":"2024-09-09T20:53:39.560Z","producer":"SKODA_MHUB","name":"change-lights","data":{"userId":"userid","vin":"vin"}}
```