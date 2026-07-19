# Python Google Health API Client Library

[![API Reference](https://img.shields.io/badge/API-Reference-blue.svg)](https://allenporter.github.io/python-google-health-api/)

An asynchronous, type-safe Python client library for the Google Health API (`health.googleapis.com/v4`). This library is designed to help developers migrate from the legacy Fitbit Web API to the Google Health API.

It exposes Google Health data types as clean, type-annotated properties on the client (e.g., `api.steps` and `api.heart_rate`).

## Features

- **Asynchronous**: Built on `aiohttp` for non-blocking asynchronous requests.
- **Type-safe**: Leverages Python dataclasses and `mashumaro` for seamless JSON serialization and deserialization, matching the exact Google Health API schemas.
- **AIP-160 Filter Support**: Built-in helper to automatically translate timestamp queries into Google API filter expressions.
- **Auto-pagination**: Paginated results wrap list endpoints and provide asynchronous iterators to traverse pages easily.

## Supported Data Types

The library supports all **36 data types** defined in the Google Health API schema:

* **Activity & Fitness**:
  * Steps (`api.steps`)
  * Distance (`api.distance`)
  * Floors (`api.floors`)
  * Active Minutes (`api.active_minutes`)
  * Active Zone Minutes (`api.active_zone_minutes`)
  * Sedentary Period (`api.sedentary_period`)
  * Altitude (`api.altitude`)
  * Swim Lengths (`api.swim_lengths_data`)
  * Exercise Logs (`api.exercise`)
  * Activity Level (`api.activity_level`)
* **Body & Health Measurements**:
  * Weight (`api.weight`)
  * Height (`api.height`)
  * BMI (`api.bmi`)
  * Body Fat (`api.body_fat`)
  * Blood Glucose (`api.blood_glucose`)
  * Core Body Temperature (`api.core_body_temperature`)
* **Nutrition & Hydration**:
  * Nutrition Log (`api.nutrition_log`)
  * Hydration Log (`api.hydration_log`)
* **Heart & Cardio Health**:
  * Heart Rate (`api.heart_rate`)
  * Daily Resting Heart Rate (`api.daily_resting_heart_rate`)
  * Heart Rate Variability (`api.heart_rate_variability`)
  * Daily Heart Rate Variability (`api.daily_heart_rate_variability`)
  * Time in Heart Rate Zone (`api.time_in_heart_rate_zone`)
  * Calories in Heart Rate Zone (`api.calories_in_heart_rate_zone`)
  * Daily Heart Rate Zones (`api.daily_heart_rate_zones`)
  * VO2 Max (`api.vo2_max`)
  * Run VO2 Max (`api.run_vo2_max`)
  * Daily VO2 Max (`api.daily_vo2_max`)
  * Electrocardiogram (ECG) (`api.electrocardiogram`)
  * Irregular Rhythm Notification (`api.irregular_rhythm_notification`)
* **Energy Expenditures**:
  * Basal Energy Burned (`api.basal_energy_burned`)
  * Active Energy Burned (`api.active_energy_burned`)
  * Total Calories (`api.total_calories`)
* **Respiratory Metrics**:
  * Daily Respiratory Rate (`api.daily_respiratory_rate`)
  * Respiratory Rate Sleep Summary (`api.respiratory_rate_sleep_summary`)
* **Sleep & Temperature**:
  * Sleep (`api.sleep`)
  * Daily Sleep Temperature Derivations (`api.daily_sleep_temperature_derivations`)


## Installation

Install the package from PyPI using `uv`:

```bash
uv pip install google-health-api
```

## Quickstart

```python
import asyncio
import aiohttp
from google_health_api.api import GoogleHealthApi
from google_health_api.auth import AbstractAuth

class SimpleAuth(AbstractAuth):
    def __init__(self, websession: aiohttp.ClientSession, access_token: str) -> None:
        super().__init__(websession)
        self._access_token = access_token

    async def async_get_access_token(self) -> str:
        return self._access_token

async def main():
    async with aiohttp.ClientSession() as session:
        # Initialize authorization wrapper with your Google OAuth 2.0 access token
        auth = SimpleAuth(session, "YOUR_ACCESS_TOKEN")
        api = GoogleHealthApi(auth)

        # 1. Fetch steps from the last 24 hours
        from datetime import datetime, timezone, timedelta
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=1)

        result = await api.steps.list(start_time=start_time, end_time=end_time)
        print("Steps:")
        for point in result.data_points:
            print(f"  Count: {point.data.count} steps")
            print(f"  Time: {point.data.start_time} to {point.data.end_time}")

        # 2. Fetch heart rate records
        hr_result = await api.heart_rate.list(start_time=start_time, end_time=end_time)
        print("Heart Rates:")
        for point in hr_result.data_points:
            print(f"  BPM: {point.data.bpm}")

if __name__ == "__main__":
    asyncio.run(main())
```

## Development and Testing

Verify code quality and type safety:

```bash
./script/lint
```

Run mock tests:

```bash
./script/test
```

Verify with a live account using the browser-based OAuth 2.0 Installed App Flow:

1. Create an OAuth client ID for a "Desktop application" in the Google Cloud Console.
2. Download the JSON key file, rename it to `client_secret.json`, and place it in the project root.
3. Authenticate and query via the command-line interface tool:
   ```bash
   # Log in via your web browser (stores credentials in token.json)
   google-health-cli login

   # List step data points
   google-health-cli steps list --days 7 --limit 5

   # List heart rate data points
   google-health-cli heart-rate list --days 7 --limit 5

   # Retrieve user profile details
   google-health-cli profile get
   ```

## Command-Line Interface (CLI)

The package installs a real binary executable `google-health-cli` designed with **Agent DX** (AI Agent Developer Experience) and **Human DX** principles.

### Key Capabilities
* **Dynamic Schema Introspection**: Let agents query request/response layouts at runtime.
  ```bash
  google-health-cli schema
  google-health-cli schema steps.list
  ```
* **Raw JSON Payloads**: Pass structured queries or write payloads directly to bypass flat CLI argument limits.
  ```bash
  # Query filtering via --params
  google-health-cli --params '{"pageSize": 5, "startTime": "2026-06-26T00:00:00Z"}' steps list

  # Mutation via --json
  google-health-cli --json '{"steps": {"count": 100, ...}}' steps create
  ```
* **Context Token Discipline**: Use fields/masking filters to prevent bloating agent reasoning limits.
  ```bash
  google-health-cli --fields "dataPoints(steps(count,interval))" steps list
  ```
* **Safety Rails & Dry-Runs**: Validate mutating requests locally before hitting the API.
  ```bash
  google-health-cli --dry-run --json '{"steps": {"count": 100, ...}}' steps create
  ```
* **Headless Integration**: Autodetects environment variables for credentials in headless agent contexts.
  ```bash
  export GOOGLE_HEALTH_CLI_TOKEN="YOUR_OAUTH_TOKEN"
  google-health-cli profile get
  ```
