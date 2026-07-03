"""Constants for the Google Health API."""

HEALTH_API_URL = "https://health.googleapis.com"


class HealthApiScope:
    """OAuth scopes for Google Health."""

    ACTIVITY_READ = (
        "https://www.googleapis.com/auth/googlehealth.activity_and_fitness.readonly"
    )
    ACTIVITY_WRITE = (
        "https://www.googleapis.com/auth/googlehealth.activity_and_fitness.writeonly"
    )

    MEASUREMENTS_READ = "https://www.googleapis.com/auth/googlehealth.health_metrics_and_measurements.readonly"
    MEASUREMENTS_WRITE = "https://www.googleapis.com/auth/googlehealth.health_metrics_and_measurements.writeonly"

    SLEEP_READ = "https://www.googleapis.com/auth/googlehealth.sleep.readonly"
    SLEEP_WRITE = "https://www.googleapis.com/auth/googlehealth.sleep.writeonly"

    NUTRITION_READ = "https://www.googleapis.com/auth/googlehealth.nutrition.readonly"
    NUTRITION_WRITE = "https://www.googleapis.com/auth/googlehealth.nutrition.writeonly"

    LOCATION_READ = "https://www.googleapis.com/auth/googlehealth.location.readonly"

    PROFILE_READ = "https://www.googleapis.com/auth/googlehealth.profile.readonly"
    PROFILE_WRITE = "https://www.googleapis.com/auth/googlehealth.profile.writeonly"

    SETTINGS_READ = "https://www.googleapis.com/auth/googlehealth.settings.readonly"
    SETTINGS_WRITE = "https://www.googleapis.com/auth/googlehealth.settings.writeonly"

    ECG_READ = "https://www.googleapis.com/auth/googlehealth.ecg.readonly"

    IRN_READ = "https://www.googleapis.com/auth/googlehealth.irn.readonly"

    USERINFO_PROFILE = "https://www.googleapis.com/auth/userinfo.profile"
    USERINFO_EMAIL = "https://www.googleapis.com/auth/userinfo.email"
