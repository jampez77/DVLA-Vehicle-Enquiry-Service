# ![Logo](https://github.com/jampez77/DVLA-Vehicle-Enquiry-Service/blob/main/logo.png "DVLA Logo") DVLA Vehicle Enquiry Service for Home Assistant

This component provides vehicle details of a specified vehicle into and adds a sensor to [Home Assistant](https://www.home-assistant.io/) which can be used in your own automations.

---

[![GitHub Release][releases-shield]][releases]
[![License][license-shield]](LICENSE.md)
[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg?style=for-the-badge)](https://github.com/custom-components/hacs)
![Project Maintenance][maintenance-shield]


Enjoying this? Help me out with a :beers: or :coffee:!

[![coffee](https://www.buymeacoffee.com/assets/img/custom_images/black_img.png)](https://www.buymeacoffee.com/whenitworks)


## Installation through [HACS](https://hacs.xyz/)
You can install the **DVLA Vehicle Enquiry Service** integration by searching for it there in HA instance.

## Manual Installation
Use this route only if you do not want to use [HACS](https://hacs.xyz/) and love the pain of manually installing regular updates.
* Add the `dvla` folder in your `custom_components` folder

## Usage

Before you can configure this sensor, you must register and obtain and API key at [VES API Registration](https://register-for-ves.driver-vehicle-licensing.api.gov.uk/).

The API is ratelimited, this is predefined when filling in the registration form under `Estimated monthly enquiry volumes` input. The default `scan interval` is every 6 hours (21600 seconds), this translates to about `62` for `Estimated monthly enquiry volumes`. 

You can change this value at any time by configuring the `scan interval` for an instance. You should take the rate limiting into account when setting the `scan interval` and vice versa.

Also make sure to select `no` for Testing otherwise you won't have access to any live data.

---
## Data 
The following attributes can be expose as attributes in HA. It's also worth mentioning that some data won't be returned if it doesn't apply to the specific vehicle.

- registrationNumber
- taxStatus
- taxDueDate
- motStatus
- make
- yearOfManufacture
- engineCapacity
- co2Emissions
- fuelType
- markedForExport
- colour
- typeApproval
- dateOfLastV5CIssued
- motExpiryDate
- wheelplan
- monthOfFirstRegistration
- artEndDate
- revenueWeight
- euroStatus
- realDrivingEmissions

---

[commits-shield]: https://img.shields.io/github/commit-activity/y/jampez77/DVLA-Vehicle-Enquiry-Services.svg?style=for-the-badge
[commits]: https://github.com/jampez77/DVLA-Vehicle-Enquiry-Service/commits/main
[license-shield]: https://img.shields.io/github/license/jampez77/DVLA-Vehicle-Enquiry-Service.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/Maintainer-Jamie%20Nandhra--Pezone-blue
[releases-shield]: https://img.shields.io/github/v/release/jampez77/DVLA-Vehicle-Enquiry-Service.svg?style=for-the-badge
[releases]: https://github.com/jampez77/DVLA-Vehicle-Enquiry-Service/releases 
