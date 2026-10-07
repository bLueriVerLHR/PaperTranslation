"""Isolated deployment identity, bounded metadata readiness and mutation tests."""

import copy
import io
import urllib.error

import pytest

from tools import pages_deploy as module

ROOT = "https://api.github.com/repos/fixture/site"
SHA = "a" * 40
ARTIFACT = {
    "id": 7,
    "name": "github-pages",
    "workflow_run": {"id": 88},
    "expired": False,
    "size_in_bytes": 123,
}


@pytest.fixture(autouse=True)
def no_wait(monkeypatch):
    monkeypatch.setattr(module.time, "sleep", lambda seconds: None)


def test_exact_upload_id_not_list_count_controls_deployment(capsys):
    calls = []

    def api(url, **kwargs):
        calls.append((url, kwargs))
        if url.endswith("/actions/artifacts/7"):
            return ARTIFACT
        if kwargs.get("method") == "POST":
            return {"id": "deployment-1", "page_url": "https://fixture.github.io/site/"}
        return {"status": "succeed"}

    assert module.deploy(api, ROOT, 7, 88, SHA, "private-oidc") == "https://fixture.github.io/site/"
    assert [url for url, _ in calls] == [
        ROOT + "/actions/artifacts/7",
        ROOT + "/pages/deployments",
        ROOT + "/pages/deployments/deployment-1",
    ]
    assert calls[1][1]["payload"]["artifact_id"] == 7
    assert "private-oidc" not in capsys.readouterr().out


def test_transient_missing_metadata_is_bounded_and_read_only():
    replies = [module.ApiError(404), {}, ARTIFACT]
    calls = []

    def api(url):
        calls.append(url)
        reply = replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply

    assert module.artifact_metadata(api, ROOT, 7, 88) == ARTIFACT
    assert len(calls) == 3 and len(set(calls)) == 1
    with pytest.raises(RuntimeError, match="no deployment was created"):
        module.artifact_metadata(lambda url: {}, ROOT, 7, 88, attempts=3)


@pytest.mark.parametrize(
    "field,value",
    [
        ("id", 8),
        ("id", True),
        ("name", "other"),
        ("workflow_run", {"id": 99}),
        ("expired", True),
        ("size_in_bytes", 0),
        ("size_in_bytes", True),
        ("size_in_bytes", 1_073_741_825),
    ],
)
def test_wrong_identity_or_size_never_creates_deployment(field, value):
    data = copy.deepcopy(ARTIFACT)
    data[field] = value
    calls = []

    def api(url, **kwargs):
        calls.append(kwargs)
        return data

    with pytest.raises(RuntimeError, match="does not match"):
        module.deploy(api, ROOT, 7, 88, SHA, "not-logged")
    assert calls == [{}]


def test_auth_failure_is_not_retried():
    calls = []

    def api(url):
        calls.append(url)
        raise module.ApiError(403)

    with pytest.raises(module.ApiError):
        module.artifact_metadata(api, ROOT, 7, 88)
    assert len(calls) == 1


def test_failed_creation_has_no_second_post():
    posts = []

    def api(url, **kwargs):
        if kwargs:
            posts.append(kwargs)
            raise module.ApiError(503)
        return ARTIFACT

    with pytest.raises(module.ApiError):
        module.deploy(api, ROOT, 7, 88, SHA, "secret")
    assert len(posts) == 1


@pytest.mark.parametrize("status", ["deployment_failed", "building"])
def test_terminal_failure_and_timeout_never_recreate(status):
    posts = []
    clock = iter([0, 0, 1, 601])

    def api(url, **kwargs):
        if url.endswith("/actions/artifacts/7"):
            return ARTIFACT
        if kwargs:
            posts.append(url)
            return {"id": "owned", "page_url": "https://fixture.github.io/"}
        return {"status": status}

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(module.time, "monotonic", lambda: next(clock))
        with pytest.raises(RuntimeError, match=r"failed|timed out"):
            module.deploy(api, ROOT, 7, 88, SHA, "secret")
    assert posts[0] == ROOT + "/pages/deployments"
    if status == "building":
        assert posts == [ROOT + "/pages/deployments", ROOT + "/pages/deployments/owned/cancel"]
    else:
        assert len(posts) == 1


@pytest.mark.parametrize("endpoint", [ROOT, "https://token.actions.githubusercontent.com/token"])
def test_transport_does_not_echo_error_body_or_authorization(monkeypatch, endpoint):
    class Opener:
        def open(self, req, timeout):
            assert req.get_header("Authorization") == "Bearer token-secret"
            expected = (
                "application/json" if "token.actions" in endpoint else "application/vnd.github+json"
            )
            assert req.get_header("Accept") == expected
            raise urllib.error.HTTPError(
                req.full_url, 403, "body-secret", {}, io.BytesIO(b"body-secret")
            )

    monkeypatch.setattr(module.urllib.request, "build_opener", lambda *args: Opener())
    with pytest.raises(module.ApiError) as caught:
        module.request(endpoint, "token-secret")
    assert "secret" not in str(caught.value)
    assert (
        module.NoRedirect().redirect_request(None, None, 302, None, None, "https://other/") is None
    )


@pytest.mark.parametrize(
    "url",
    ["http://api.github.com/", "https://other.invalid/", "https://user:secret@api.github.com/"],
)
def test_transport_rejects_unsafe_endpoints_before_auth(monkeypatch, url):
    monkeypatch.setattr(
        module.urllib.request, "build_opener", lambda *args: pytest.fail("No transport expected")
    )
    with pytest.raises(ValueError, match="trusted GitHub HTTPS"):
        module.request(url, "not-sent")


def test_cli_job_token_oidc_and_output(monkeypatch, tmp_path, capsys):
    output = tmp_path / "outputs.txt"
    monkeypatch.setattr(
        module.os,
        "environ",
        {
            "GITHUB_ACTIONS": "true",
            "GITHUB_REPOSITORY": "fixture/site",
            "GITHUB_RUN_ID": "88",
            "GITHUB_SHA": SHA,
            "ACTIONS_ID_TOKEN_REQUEST_URL": "https://token.actions.githubusercontent.com/token",
            "ACTIONS_ID_TOKEN_REQUEST_TOKEN": "request-secret",
            "GH_TOKEN": "job-secret",
            "GITHUB_OUTPUT": str(output),
        },
    )
    tokens = []

    def request(url, token, **kwargs):
        tokens.append(token)
        if "token.actions" in url:
            return {"value": "oidc-secret"}
        if url.endswith("/actions/artifacts/7"):
            return ARTIFACT
        if kwargs.get("method") == "POST":
            assert kwargs["payload"]["oidc_token"] == "oidc-secret"  # noqa: S105 (synthetic fixture)
            return {"id": "owned", "page_url": "https://fixture.github.io/site/"}
        return {"status": "succeed"}

    monkeypatch.setattr(module, "request", request)
    assert module.main(["--artifact-id", "7"]) == 0
    assert tokens == ["request-secret", "job-secret", "job-secret", "job-secret"]
    assert output.read_text() == "page_url=https://fixture.github.io/site/\n"
    assert "secret" not in capsys.readouterr().out


def test_cli_rejects_non_ci_without_network(monkeypatch):
    monkeypatch.setattr(
        module.os,
        "environ",
        {"GITHUB_REPOSITORY": "fixture/site", "GITHUB_RUN_ID": "88", "GITHUB_SHA": SHA},
    )
    monkeypatch.setattr(
        module, "request", lambda *args, **kwargs: pytest.fail("No request expected")
    )
    with pytest.raises(SystemExit):
        module.main(["--artifact-id", "7"])
