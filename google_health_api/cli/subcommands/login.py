"""Login subcommand for Google Health CLI."""

import json
import os
import sys

from google_auth_oauthlib.flow import Flow, InstalledAppFlow

from ..auth import CLIENT_SECRET_FILE, SCOPES, save_credentials
from ..utils import print_error_json, print_json


def cmd_login(args) -> None:
    """Execute interactive OAuth login flow."""
    if not os.path.exists(CLIENT_SECRET_FILE):
        print_error_json(
            f"Client secrets file '{CLIENT_SECRET_FILE}' not found.",
            status="NOT_FOUND",
        )

    if not sys.stdin.isatty():
        print_error_json(
            "Cannot run interactive login in a headless environment.",
            status="FAILED_PRECONDITION",
        )

    with open(CLIENT_SECRET_FILE, "r") as f:
        client_secrets_data = json.load(f)

    is_web = "web" in client_secrets_data

    if is_web:
        redirect_uris = client_secrets_data["web"].get("redirect_uris", [])
        redirect_uri = redirect_uris[0] if redirect_uris else "http://localhost:8080/"

        flow = Flow.from_client_secrets_file(
            CLIENT_SECRET_FILE,
            scopes=SCOPES,
            redirect_uri=redirect_uri,
        )
        authorization_url, _ = flow.authorization_url(
            access_type="offline",
            prompt="consent",
        )
        print("Web-based authentication flow:")
        print(f"URL: {authorization_url}")
        redirect_response = input("Redirected URL or auth code: ").strip()

        if not redirect_response:
            print_error_json(
                "Redirected URL cannot be empty.", status="INVALID_ARGUMENT"
            )

        os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
        os.environ["OAUTHLIB_RELAX_TOKEN_SCOPE"] = "1"

        if "code=" in redirect_response or redirect_response.startswith("http"):
            flow.fetch_token(authorization_response=redirect_response)
        else:
            flow.fetch_token(code=redirect_response)
        credentials = flow.credentials
    else:
        flow = InstalledAppFlow.from_client_secrets_file(
            CLIENT_SECRET_FILE,
            scopes=SCOPES,
        )
        credentials = flow.run_local_server(port=0)

    save_credentials(credentials)
    print_json({"status": "SUCCESS", "message": "Logged in successfully."})
