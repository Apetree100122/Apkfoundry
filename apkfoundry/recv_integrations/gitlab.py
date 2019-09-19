# SPDX-License-Identifier: GPL-2.0-only
# Copyright (c) 2019 Max Rees
# See LICENSE for more information.
import logging # getLogger

from .. import get_config, EStatus, db_queue
from ..objects import JSONSchema, Push, MergeRequest

_LOGGER = logging.getLogger(__name__)

SENTINEL_COMMIT = "0000000000000000000000000000000000000000"

# Notes for changes since GitLab 8.0.5:
# https://gitlab.com/gitlab-org/gitlab-ce/blob/v8.0.5/doc/web_hooks/web_hooks.md
# * repository -> project
# * push: added user_username (previously only user_email available)
# * note, mr: use git_http_url instead of http_url

class GitlabPush(JSONSchema):
    schema = {
        "after": str,
        "before": str,
        "commits": [
            {
                "url": str,
            },
        ],
        "ref": str,
        "project": {
            "git_http_url": str,
        },
        "user_username": str,
    }

    __slots__ = tuple(schema.keys())

    def to_event(self, project):
        return Push(
            id=None,
            project=project,
            clone=self.get_url(),
            target=self["ref"].replace("refs/heads/", "", 1),
            revision=self["after"],
            user=self["user_username"],
            reason=self["commits"][-1]["url"],
            status=EStatus.NEW,

            before=self["before"],
            after=self["after"],
        )

    def get_url(self):
        return self["project"]["git_http_url"]

    def is_valid(self, project, config):
        if not self["commits"]:
            _LOGGER.warning("[%s] no commits attached", project)
            return False

        if not self["ref"].startswith("refs/heads/"):
            _LOGGER.warning(
                "[%s] skipping non-branch %s", project, self["ref"]
            )
            return False

        branch = self["ref"].replace("refs/heads/", "", 1)
        branches = config.getlist("push_branches")
        if branches and branch not in branches:
            _LOGGER.warning("[%s] push branch not on allowed list", project)
            return False

        return True

class _GitlabAbstractMergeRequest(JSONSchema):
    def to_event(self, project):
        return MergeRequest(
            id=None,
            project=project,
            clone=self.get_url(),
            target=self[self._root]["target_branch"],
            mrid=str(self[self._root]["iid"]),
            mrclone=self[self._root]["source"]["git_http_url"],
            mrbranch=self[self._root]["source_branch"],
            revision=self[self._root]["last_commit"]["id"],
            user=self["user"]["username"],
            reason=self["object_attributes"]["url"],
            status=EStatus.NEW,
        )

    def get_url(self):
        return self[self._root]["target"]["git_http_url"]

    def is_valid(self, project, config):
        raise NotImplementedError

class GitlabMergeRequest(_GitlabAbstractMergeRequest):
    schema = {
        "object_attributes": {
            "iid": int,
            "last_commit": {
                "id": str,
            },
            "source": {
                "git_http_url": str,
            },
            "source_branch": str,
            "target": {
                "git_http_url": str,
            },
            "target_branch": str,
            "url": str,
        },
        "user": {
            "username": str,
        },
    }

    _root = "object_attributes"
    __slots__ = tuple(schema.keys())

    def is_valid(self, project, config):
        branches = config.getlist("mr_branches")
        if branches and self["object_attributes"]["target_branch"] not in branches:
            _LOGGER.warning("[%s] mr branch not on allowed list", project)
            return False

        users = config.getlist("mr_users")
        if users and self["user"]["username"] not in users:
            _LOGGER.warning("[%s] mr user not on allowed list", project)
            return False

        return True

class GitlabNote(_GitlabAbstractMergeRequest):
    schema = {
        "merge_request": {
            "iid": int,
            "last_commit": {
                "id": str,
            },
            "source": {
                "git_http_url": str,
            },
            "source_branch": str,
            "target": {
                "git_http_url": str,
            },
            "target_branch": str,
        },
        "object_attributes": {
            "note": str,
            "noteable_type": "MergeRequest",
            "url": str,
        },
        "user": {
            "username": str,
        },
    }

    _root = "merge_request"
    __slots__ = tuple(schema.keys())

    def is_valid(self, project, config):
        users = config.getlist("note_users")
        if users and self["user"]["username"] not in users:
            _LOGGER.warning("[%s] note user not on allowed list", project)
            return False

        note = self["object_attributes"]["note"]
        if config.get("note_keyword") not in note:
            _LOGGER.warning("[%s] note does not contain keyword", project)
            return False

        return True

_EVENTS = {
    "push": {
        "class": GitlabPush,
        "event": "push",
    },
    "merge_request": {
        "class": GitlabMergeRequest,
        "event": "mr",
    },
    "note": {
        "class": GitlabNote,
        "event": "note",
    },
}

def gitlab_recv_hook(payload):
    try:
        assert "object_kind" in payload, \
            "Missing object_kind"
        kind = payload["object_kind"]

        assert isinstance(kind, str), "object_kind must be str"
        assert kind in _EVENTS, f"unknown object_kind {kind}"

        if kind == "note" and "merge_request" not in payload:
            _LOGGER.debug("skipping note that isn't on an mr")
            return

        payload = _EVENTS[kind]["class"](**payload)
        url = payload.get_url()
        option = _EVENTS[kind]["event"]

    except AssertionError as e:
        _LOGGER.exception("invalid payload '%s'", payload, exc_info=e)
        return

    try:
        config = get_config(url)
    except KeyError:
        _LOGGER.warning("[%s] unknown project", url)
        return
    try:
        project = config["name"]
    except KeyError:
        _LOGGER.warning("[%s] no project name", url)
        return

    if not config.getboolean(option):
        _LOGGER.warning("[%s] %s is not enabled", project, option)
        return

    if not payload.is_valid(project, config):
        return

    payload = payload.to_event(project)
    db_queue.put(payload)