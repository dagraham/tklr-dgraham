#!/usr/bin/env python3

"""Sync recent_changes.md content to a GitHub Discussion body."""

from __future__ import annotations

import json
import os
import sys
import urllib.request
from pathlib import Path

API_URL = "https://api.github.com/graphql"
RECENT_CHANGES_PATH = Path("recent_changes.md")


def fail(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    raise SystemExit(1)


def graphql(token: str, query: str, variables: dict) -> dict:
    body = json.dumps({"query": query, "variables": variables}).encode("utf-8")
    req = urllib.request.Request(
        API_URL,
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/vnd.github+json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        raw = resp.read().decode("utf-8")
    data = json.loads(raw)
    if "errors" in data and data["errors"]:
        fail(f"GraphQL error: {data['errors']}")
    return data.get("data", {})


def get_discussion_id(token: str, owner: str, repo: str, number: int) -> str:
    query = """
    query($owner:String!, $repo:String!, $number:Int!) {
      repository(owner:$owner, name:$repo) {
        discussion(number:$number) {
          id
        }
      }
    }
    """
    data = graphql(
        token,
        query,
        {"owner": owner, "repo": repo, "number": number},
    )
    discussion = (data.get("repository") or {}).get("discussion")
    if not discussion or not discussion.get("id"):
        fail(
            f"Could not find discussion number {number} in "
            f"{owner}/{repo}. Check DISCUSSION_NUMBER."
        )
    return discussion["id"]


def update_discussion_body(token: str, discussion_id: str, body: str) -> str:
    mutation = """
    mutation($discussionId:ID!, $body:String!) {
      updateDiscussion(input:{discussionId:$discussionId, body:$body}) {
        discussion {
          url
        }
      }
    }
    """
    data = graphql(
        token,
        mutation,
        {"discussionId": discussion_id, "body": body},
    )
    discussion = (data.get("updateDiscussion") or {}).get("discussion") or {}
    url = discussion.get("url", "")
    if not url:
        fail("Discussion update succeeded but did not return a URL.")
    return url


def main() -> None:
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    repo_full = os.environ.get("GITHUB_REPOSITORY", "").strip()
    discussion_number_raw = os.environ.get("DISCUSSION_NUMBER", "").strip()

    if not token:
        fail("GITHUB_TOKEN is required.")
    if not repo_full or "/" not in repo_full:
        fail("GITHUB_REPOSITORY must be set as owner/repo.")
    if not discussion_number_raw:
        fail("DISCUSSION_NUMBER is required.")

    try:
        discussion_number = int(discussion_number_raw)
    except ValueError:
        fail("DISCUSSION_NUMBER must be an integer.")

    if not RECENT_CHANGES_PATH.exists():
        fail(f"Missing {RECENT_CHANGES_PATH}.")
    content = RECENT_CHANGES_PATH.read_text(encoding="utf-8").strip()
    if not content:
        fail(f"{RECENT_CHANGES_PATH} is empty.")

    owner, repo = repo_full.split("/", 1)
    discussion_id = get_discussion_id(token, owner, repo, discussion_number)
    url = update_discussion_body(token, discussion_id, content)
    print(f"Updated discussion: {url}")


if __name__ == "__main__":
    main()
