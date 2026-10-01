from unittest import mock

import pytest

from tklr import use_system
from tklr.use_system import _looks_like_url


@pytest.mark.parametrize(
    "target",
    [
        "https://example.com",
        "mailto:a@b.c",
        "mu4e:msgid:a@b.com",
        "notmuch://?query=id:a@b",
        "message:%3Cabc@x%3E",
        "org-protocol:/store-link?url=x",
    ],
)
def test_scheme_targets_are_urls(target):
    assert _looks_like_url(target)


@pytest.mark.parametrize(
    "target",
    [
        "~/notes/file.md",
        "/etc/hosts",
        "relative/file.txt",
        r"C:\Users\x\file.txt",
        "",
    ],
)
def test_paths_are_not_urls(target):
    assert not _looks_like_url(target)


def test_existing_file_with_colon_is_a_path(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "notes:draft.txt").write_text("x")
    assert not _looks_like_url("notes:draft.txt")


def test_open_with_default_passes_scheme_url_through(monkeypatch):
    monkeypatch.setattr(use_system.platform, "system", lambda: "Linux")
    with mock.patch.object(use_system.subprocess, "Popen") as popen:
        use_system.open_with_default("mu4e:msgid:abc@example.com")
    assert popen.call_args[0][0] == ["xdg-open", "mu4e:msgid:abc@example.com"]
