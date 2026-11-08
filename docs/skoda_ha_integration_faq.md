# Škoda Home Assistant Integration: FAQ

## How to use this FAQ
These are shared answers to the most common questions about the new Škoda integration for Home Assistant. They are meant for Škoda EV Lounge and for the community developers who support the previous integration, so everyone answers in the same way.
Feel free to copy any answer as it stands or adapt the wording to your channel. Please keep the facts unchanged. If a question comes up that is not covered here, let us know and we will add it.

## About the new integration
**What is the new Škoda integration for Home Assistant?**
It is a dedicated HomeAssistant Core integration that brings data from your connected Škoda into Home Assistant. It runs on our official B2C API, which was created specifically for smart home use. It becomes part of Home Assistant Core with release 2026.11.

**Who built it?**
It was developed together with the Mobility Lab at VSB Technical University of Ostrava ([VSB-TUO](<https://www.vsb.cz/en/>), [Mobility Lab](<https://livinglab.vsb.cz/mobility-lab/>)) and the community developers behind the previous integration. A big thank you to all of them.

**When can I use it?**
The first version is available now in the Home Assistant Core beta channel. Stable Home Assistant releases come out on the first Wednesday of each month, so the integration arrives in the stable channel with Home Assistant Core 2026.11.

**Which cars are supported?**
All connected Škoda vehicles, not only EVs. The data you see depends on your car and on your active Škoda Connect licences.

**How does development continue after the first release?**
Home Assistant integrations usually grow step by step. They are not released only once everything is done, and in practice an integration is never really finished. Each new development increment (pull request) adds more, and new features arrive in the monthly feature releases.

## Features
**What can the integration do today?**
The first version reads vehicle information and shows it as sensors in Home Assistant. Control functions are not part of the first version.

**Is the state of charge (SOC) available?**
Yes. The state of charge is available in the new integration, so you can build smart charging automations on it.

**Why does the first version only read data?**
The Home Assistant maintainers recommended starting with a first, focused version and then growing it like a snowball through further pull requests. That is why reading data through sensors came first and control functions follow later.

**Will I be able to control charging or heating?**
Yes, this is high on our priority list. We are not able to give an exact release date yet. New features arrive in monthly Home Assistant feature releases, not in bugfix updates, so the earliest possible release for new functions is a later monthly version after 2026.11.

## Previous API and timeline
**When will the previous API be switched off?**
In the last week of November 2026. After that, the previous community integration will stop receiving data.

**What do you recommend I do now?**
We recommend moving over to the new integration before the end of November, so your sensors and dashboards keep working.

## Scope and limits
**How many requests can the integration make?**
Currently 20 requests per hour per vehicle (VIN). We are looking into possibilities for increasing this limit.

**Can more data be added to the API?**
Never say never. We listen to your feedback. If we see a clear need for an additional dataset in the B2C API, we will consider adding it, and it would then of course appear in the Home Assistant integration as well.

## Feedback and next steps
**Where can I share feedback or ideas for new features?**
In the Škoda EV Lounge community on Facebook. Tell us which functions matter most to you, as this helps us set the right priorities.
We also plan to have a dedicated page on our [website](<http://www.skoda-auto.com>) given to the B2C API and HomeAssistant integration for customers not using Facebook or not being in the EV Lounge group.
Alternatively, you can report issues or request new features via [HomeAssistant GitHub](<https://github.com/orgs/home-assistant/discussions>), just make sure to specify that it is related to Škoda integration and check if someone else have not requested it or reported the same bug before.
