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

## Contributing

Contirbutions are welcome from everyone! By contributing to this project, you help improve it and make it more useful for the community. Here's how you can get involved:

### How to Contribute

1. **Report Bugs**: If you encounter a bug, please open an issue with details about the problem and how to reproduce it.
2. **Suggest Features**: Have an idea for a new feature? I'd love to hear about it! Please open an issue to discuss it.
3. **Submit Pull Requests**: If you'd like to contribute code:
   - Fork the repository and create your branch from `main`.
   - Make your changes in the new branch.
   - Open a pull request with a clear description of what you’ve done.

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
## Services (2025.12.4+)
Huge thanks to [ITSpecialist111](https://github.com/ITSpecialist111) who added a Home Assistant service to allow for manually looking up vehicle licence plates.

Service call:

`dvla.lookup`

Behaviour:
* Accepts a registration number
* Optionally accepts an API key (otherwise uses the configured entry)
* Performs a single DVLA Vehicle Enquiry API call
* Returns the raw JSON response using supports_response=True

[commits-shield]: https://img.shields.io/github/commit-activity/y/jampez77/DVLA-Vehicle-Enquiry-Services.svg?style=for-the-badge
[commits]: https://github.com/jampez77/DVLA-Vehicle-Enquiry-Service/commits/main
[license-shield]: https://img.shields.io/github/license/jampez77/DVLA-Vehicle-Enquiry-Service.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/Maintainer-Jamie%20Nandhra--Pezone-blue
[releases-shield]: https://img.shields.io/github/v/release/jampez77/DVLA-Vehicle-Enquiry-Service.svg?style=for-the-badge
[releases]: https://github.com/jampez77/DVLA-Vehicle-Enquiry-Service/releases 
