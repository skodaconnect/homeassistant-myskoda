# Design

## Inner workings
This integration uses a combination of push and pull techniques, and it does so in the following manner:

1. Upon launch, we contact MySkoda servers to collect data about your car. This allows us to determine which entities we need to create.
   This means we never contact your car directly. Skoda has no way for users to connect to the car via the OTA/GSM/LTE connection (that we know of).

2. When we know about your car, we connect to the MySkoda servers and tell them we want to receive events for your car via MQTT.

3. Once we are fully initialised, we start a regular poll. This is behaviour that's common to most HomeAssistant integrations.
   MySkoda servers are polled on a default interval of 30 minutes. This may seem slow, but before you adjust it, read the next point please.

4. By listening to the events that come from your car, we have a steady stream of updates while your car is operating.
   Example events are: Unlock/Lock/Odometer update/SoC update/GPS update.
   When we receive an event, we process the data that's in the event directly and contact MySkoda servers to refresh the data relevant to the event.
   For instance: When we receive an Odometer update event, we ask MySkoda what the odometer is now and then update that sensor.
   Or: Sometimes we receive an error event from the car. At that point, we request a full update so you get the most recent state as soon as the error occurred.

5. Sometimes, we receive more than one sensor update. We then update all relevant sensors.

6. The now scheduled update gets delayed by the default interval of 30 minutes.

7. When 30 minutes have passed and we have not received any event, we request a full update from the MySkoda servers. All entities are refreshed.

8. We keep on listening for events and return to step 4 in this list.
