"""Deploy one CI-uploaded Pages artifact by ID, without artifact-list discovery."""

from __future__ import annotations

import argparse
import json
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit

API = "https://api.github.com"
TERMINAL_ERRORS = {
    "deployment_failed",
    "deployment_perms_error",
    "deployment_content_failed",
    "deployment_cancelled",
    "deployment_lost",
}


class ApiError(RuntimeError):
    """Expose only an HTTP status, never tokens or response bodies."""

    def __init__(self, status: int) -> None:
        self.status = status
        super().__init__(f"GitHub request failed (HTTP {status}); no mutation retry")


class NoRedirect(urllib.request.HTTPRedirectHandler):
    """Do not forward authorization headers through redirects."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def request(url: str, token: str, *, method: str = "GET", payload: dict | None = None) -> dict:
    """Send one normal-TLS JSON request, with no automatic mutation retries."""
    endpoint = urlsplit(url)
    if (
        endpoint.scheme != "https"
        or not endpoint.hostname
        or endpoint.username
        or endpoint.password
        or not (
            endpoint.hostname == "api.github.com"
            or endpoint.hostname.endswith(".actions.githubusercontent.com")
        )
    ):
        raise ValueError("Deployment requests require a trusted GitHub HTTPS endpoint")
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": (
            "application/vnd.github+json"
            if endpoint.hostname == "api.github.com"
            else "application/json"
        ),
        "User-Agent": "PaperTranslation-Pages-deployment",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    body = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers=headers, method=method)  # noqa: S310
    try:
        with urllib.request.build_opener(NoRedirect()).open(req, timeout=25) as response:
            raw = response.read(1_048_577)
    except urllib.error.HTTPError as error:
        raise ApiError(error.code) from None
    except (urllib.error.URLError, OSError):
        raise RuntimeError("GitHub connection failed; mutation outcome may be unknown") from None
    if len(raw) > 1_048_576:
        raise RuntimeError("GitHub response exceeds deployment metadata limit")
    try:
        value = json.loads(raw)
    except (UnicodeError, ValueError):
        raise RuntimeError("Invalid GitHub JSON response") from None
    if not isinstance(value, dict):
        raise RuntimeError("Invalid GitHub metadata object")
    return value


def artifact_metadata(api, root: str, artifact_id: int, run_id: int, *, attempts: int = 6) -> dict:
    """Read the exact uploaded ID; briefly tolerate missing visibility, not wrong identity."""
    for attempt in range(attempts):
        try:
            data = api(f"{root}/actions/artifacts/{artifact_id}")
        except ApiError as error:
            if error.status not in {404, 502, 503, 504}:
                raise
            data = {}
        required = {"id", "name", "workflow_run", "expired", "size_in_bytes"}
        if (
            required <= data.keys()
            and isinstance(data["workflow_run"], dict)
            and "id" in data["workflow_run"]
        ):
            if (
                type(data["id"]) is not int
                or data["id"] != artifact_id
                or data["name"] != "github-pages"
                or type(data["workflow_run"]["id"]) is not int
                or data["workflow_run"]["id"] != run_id
                or data["expired"] is not False
                or type(data["size_in_bytes"]) is not int
                or not 0 < data["size_in_bytes"] <= 1_073_741_824
            ):
                raise RuntimeError(
                    "Artifact identity, run, expiry or size does not match this upload"
                )
            return data
        if attempt + 1 < attempts:
            time.sleep(2)
    raise RuntimeError("Uploaded artifact metadata is not ready; no deployment was created")


def deploy(
    api, root: str, artifact_id: int, run_id: int, sha: str, oidc: str, *, timeout: int = 600
) -> str:
    """Verify the uploaded artifact, create exactly once and observe that deployment only."""
    artifact_metadata(api, root, artifact_id, run_id)
    data = api(
        f"{root}/pages/deployments",
        method="POST",
        payload={"artifact_id": artifact_id, "pages_build_version": sha, "oidc_token": oidc},
    )
    deployment_id = str(data.get("id") or sha)
    page_url = data.get("page_url", "")
    if not re.fullmatch(r"[A-Za-z0-9_-]+", deployment_id):
        raise RuntimeError("Invalid created deployment identity; do not create again")
    if not isinstance(page_url, str) or any(ord(char) < 32 for char in page_url):
        raise RuntimeError("Invalid deployment page URL; do not create again")
    url = urlsplit(page_url)
    if url.scheme != "https" or not url.netloc or url.username or url.password:
        raise RuntimeError("Invalid deployment page URL; do not create again")
    deadline = time.monotonic() + timeout
    last_status = None
    while time.monotonic() < deadline:
        try:
            state = api(f"{root}/pages/deployments/{deployment_id}").get("status")
        except ApiError as error:
            if error.status not in {404, 502, 503, 504}:
                raise
            state = "status_not_ready"
        if not isinstance(state, str) or not state:
            raise RuntimeError("Missing deployment status; inspect the created deployment")
        if state != last_status:
            print(f"Pages deployment {deployment_id}: {state}")
            last_status = state
        if state == "succeed":
            return page_url
        if state in TERMINAL_ERRORS:
            raise RuntimeError(f"Pages deployment failed: {state}")
        time.sleep(min(5, max(0, deadline - time.monotonic())))
    # Cancel only the deployment created by this invocation, as the official action does.
    api(f"{root}/pages/deployments/{deployment_id}/cancel", method="POST")
    raise RuntimeError("Pages deployment timed out; no new deployment will be created")


def main(argv: list[str] | None = None) -> int:
    """Use the ordinary Actions job token and OIDC without logging credentials."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-id", required=True)
    args = parser.parse_args(argv)
    try:
        env = os.environ
        repo, run, sha = env["GITHUB_REPOSITORY"], env["GITHUB_RUN_ID"], env["GITHUB_SHA"]
        if env.get("GITHUB_ACTIONS") != "true" or env.get("GITHUB_API_URL", API) != API:
            raise ValueError("This entry point requires a GitHub.com Actions job")
        if not re.fullmatch(r"[\w.-]+/[\w.-]+", repo, re.ASCII):
            raise ValueError("Invalid CI repository identity")
        if not re.fullmatch(r"[1-9]\d*", run) or not re.fullmatch(r"[1-9]\d*", args.artifact_id):
            raise ValueError("Invalid uploaded artifact/run identity")
        if not re.fullmatch(r"[0-9a-f]{40}", sha):
            raise ValueError("Invalid CI build commit")
        oidc_url = env["ACTIONS_ID_TOKEN_REQUEST_URL"]
        parsed = urlsplit(oidc_url)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or not parsed.hostname.endswith(".actions.githubusercontent.com")
            or parsed.username
            or parsed.password
        ):
            raise ValueError("Invalid CI OIDC endpoint")
        oidc = request(oidc_url, env["ACTIONS_ID_TOKEN_REQUEST_TOKEN"]).get("value")
        if not isinstance(oidc, str) or not oidc:
            raise ValueError("CI did not return an OIDC token")
        token = env["GH_TOKEN"]

        def api(url, **kwargs):
            return request(url, token, **kwargs)

        page_url = deploy(api, f"{API}/repos/{repo}", int(args.artifact_id), int(run), sha, oidc)
        with Path(env["GITHUB_OUTPUT"]).open("a", encoding="utf-8", newline="\n") as output:
            output.write(f"page_url={page_url}\n")
        print(f"Pages deployed: {page_url}")
        return 0
    except KeyError:
        parser.exit(1, "Deployment requires complete GitHub Actions runtime credentials\n")
    except (ValueError, RuntimeError, OSError) as error:
        parser.exit(1, f"Deployment failed: {error}\n")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
