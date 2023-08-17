from __future__ import annotations

import configparser
import json
import urllib
from typing import Any, Dict

import requests


class JiraAPI:
    """
    Utility for interacting with the Jira API
    See https://docs.atlassian.com/software/jira/docs/api/REST/8.5.13/
    """

    def __init__(
        self, config: configparser.ConfigParser, config_section: str = "JIRA"
    ) -> None:
        self.base = config.get(config_section, "BASE_URL")
        self.project = config.get(config_section, "PROJECT", fallback="MAR")
        self.user = config.get(config_section, "USER")
        self.api_token = config.get(config_section, "API_TOKEN")
        self.epic_field = config.get(config_section, "EPIC_FIELD")
        self.epic_name_field = config.get(config_section, "EPIC_NAME_FIELD")
        self.sprint_field = config.get(config_section, "SPRINT_FIELD")
        self.board_id = config.get(config_section, "BOARD_ID")
        self.priority = config.get(config_section, "PRIORITY")

    def _api_request(self, method: str, query: str, *args: str, **kwargs: Any) -> dict:
        url = urllib.parse.urlunsplit(
            ("https", self.base, query.format(*args), None, None)
        )
        try:
            r = requests.request(
                method,
                url,
                headers={"Authorization": f"Bearer {self.api_token}"},
                **kwargs,
            )
            # print(f'\n{r.json()}\n{method} {url}\n{json.dumps(kwargs.get("json"), sort_keys=True, indent=4)}')
            r.raise_for_status()
        except Exception as ex:
            msg = "Check your VPN connection and that user and api token are specified in the config"
            msg += f'\n{r.text}\n{method} {url}\n{json.dumps(kwargs.get("json"), sort_keys=True, indent=4)}'
            raise Exception(msg) from ex
        return r.json() if r.text else {}

    def get_comment(self, ticket: str) -> dict:
        return self._api_request("GET", "/rest/api/2/issue/{}/comment", ticket)

    def add_comment(self, ticket: str, comment: str) -> dict:
        return self._api_request(
            "POST", "/rest/api/2/issue/{}/comment", ticket, json={"body": comment}
        )

    def get_ticket(self, ticket: str) -> dict:
        return self._api_request("GET", "/rest/api/2/issue/{}", ticket)

    def _get_sprint(self, board_id: str) -> dict:
        return self._api_request(
            "GET", "rest/agile/1.0/board/{}/sprint?state=future", board_id
        )

    def _get_next_sprint(self, board_id: str) -> str:
        upcoming_sprints = self._get_sprint(board_id).get("values", [])
        next_sprint: dict = next(iter(upcoming_sprints), {})
        return next_sprint.get("id", "")

    def _set_parent(self, parent):
        return {
            "issuelinks": [
                {
                    "add": {
                        "type": {
                            "name": "Initiative",
                            "inward": "Parent of",
                            "outward": "Child of",
                        },
                        "inwardIssue": {"key": parent},
                    }
                }
            ]
        }

    def set_parent(self, ticket, parent):
        return self._api_request(
            "PUT",
            "/rest/api/2/issue/{}",
            ticket,
            json={"update": self._set_parent(parent)},
        )

    def set_epic(self, ticket: str, parent_epic: str) -> dict:
        return self._api_request(
            "PUT",
            "/rest/api/2/issue/{}",
            ticket,
            json={"fields": {self.epic_field: parent_epic}},
        )

    def create_ticket(
        self,
        title: str,
        description: str | None,
        issue_type: str | None,
        epic: str | None,
        project: str | None,
    ) -> dict:
        body = {
            "fields": {
                "project": {"key": project or self.project},
                "summary": title,
                "description": description or title,
                "issuetype": {"name": issue_type or "Story"},
            }
        }

        if issue_type == "Epic":
            body["fields"].update({self.epic_name_field: title})

        if epic:
            body["fields"].update({self.epic_field: epic})

        if parent:
            body["update"] = self._set_parent(parent)

        body["fields"].update({"priority": {"name": self.priority}})

        if issue_type != "Epic":
            next_sprint = self._get_next_sprint(self.board_id)
            if next_sprint:
                body["fields"].update({self.sprint_field: next_sprint})

        return self._api_request("POST", "/rest/api/2/issue", json=body)
