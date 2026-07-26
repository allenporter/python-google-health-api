"""Login subcommand for Google Health CLI."""

import json
import os
import sys
from collections.abc import Callable

from google_auth_oauthlib.flow import Flow, InstalledAppFlow

from ..auth import CLIENT_SECRET_FILE, SCOPES, save_credentials
from ..utils import print_error_json, print_json


def cmd_login(
    args,
    client_secret_file: str | None = None,
    token_file: str | None = None,
    is_tty: bool | None = None,
    input_func: Callable[[str], str] | None = None,
) -> None:
    """Execute interactive OAuth login flow."""
    secret_path = client_secret_file or CLIENT_SECRET_FILE
    if not os.path.exists(secret_path):
        print_error_json(
            f"Client secrets file '{secret_path}' not found.",
            status="NOT_FOUND",
        )

    tty = is_tty if is_tty is not None else sys.stdin.isatty()
    if not tty:
        print_error_json(
            "Cannot run interactive login in a headless environment.",
            status="FAILED_PRECONDITION",
        )

    with open(secret_path, "r") as f:
        client_secrets_data = json.load(f)

    is_web = "web" in client_secrets_data

    if is_web:
        redirect_uris = client_secrets_data["web"].get("redirect_uris", [])
        redirect_uri = redirect_uris[0] if redirect_uris else "http://localhost:8080/"

        flow = Flow.from_client_secrets_file(
            secret_path,
            scopes=SCOPES,
            redirect_uri=redirect_uri,
        )
        authorization_url, _ = flow.authorization_url(
            access_type="offline",
            prompt="consent",
        )
        print("Web-based authentication flow:")
        print(f"URL: {authorization_url}")
        inp = input_func or input
        redirect_response = inp("Redirected URL or auth code: ").strip()

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
            secret_path,
            scopes=SCOPES,
        )
        credentials = flow.run_local_server(port=0)

    save_credentials(credentials, token_file=token_file)
    print_json({"status": "SUCCESS", "message": "Logged in successfully."})
