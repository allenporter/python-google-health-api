# Python Google Health API Client Library

An asynchronous, type-safe Python client library for the Google Health API (`health.googleapis.com/v4`). This library is designed to help developers migrate from the legacy Fitbit Web API to the Google Health API.

It exposes Google Health data types as clean, type-annotated properties on the client (e.g., `api.steps` and `api.heart_rate`).

## Features

- **Asynchronous**: Built on `aiohttp` for non-blocking asynchronous requests.
- **Type-safe**: Leverages Python dataclasses and `mashumaro` for seamless JSON serialization and deserialization, matching the exact Google Health API schemas.
- **AIP-160 Filter Support**: Built-in helper to automatically translate timestamp queries into Google API filter expressions.
- **Auto-pagination**: Paginated results wrap list endpoints and provide asynchronous iterators to traverse pages easily.

## Supported Data Types

Currently supported data types:
* **Steps** (`api.steps`)
* **Heart Rate** (`api.heart_rate`)

## Installation

Install the package locally using `uv`:

```bash
uv pip install .
```

> [!NOTE]
> TODO: Once published to PyPI, this will be installable via `uv pip install google-health-api`.

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

Verify with a live sandbox account (requires set up of the `GOOGLE_HEALTH_ACCESS_TOKEN` environment variable):

```bash
export GOOGLE_HEALTH_ACCESS_TOKEN="your-oauth-token"
python examples/sandbox_verify.py
```
