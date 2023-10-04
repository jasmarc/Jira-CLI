from __future__ import annotations

import base64
import configparser
import json
import logging
import re
import urllib
import urllib.parse
from enum import Enum
from typing import Any

import requests


class SprintPosition(Enum):
    NEXT_SPRINT = "next sprint"
    TOP_OF_BACKLOG = "top of backlog"
    BOTTOM_OF_BACKLOG = "bottom of backlog"


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
        self.auth = config.get(config_section, "AUTH")
        self.api_token = config.get(config_section, "API_TOKEN")
        self.epic_field = config.get(config_section, "EPIC_FIELD")
        self.epic_name_field = config.get(config_section, "EPIC_NAME_FIELD")
        self.sprint_field = config.get(config_section, "SPRINT_FIELD")
        self.board_id = config.get(config_section, "BOARD_ID")
        self.priority = config.get(config_section, "PRIORITY")
        self.custom_fields = self._load_custom_fields(config, config_section)
        self.logger = logging.getLogger(__name__)

    @staticmethod
    def _load_custom_fields(
            config: configparser.ConfigParser, config_section: str
    ) -> dict:
        custom_fields_section = config.get(config_section, "CUSTOM_FIELDS")
        field_value_pairs = custom_fields_section.split(",")
        custom_fields = {}
        for field_value_pair in field_value_pairs:
            field, value = field_value_pair.split("=")
            try:
                custom_fields[field] = json.loads(value)
            except json.JSONDecodeError:
                custom_fields[field] = value
        return custom_fields

    def _api_request(self, method: str, query: str, *args: str, **kwargs: Any) -> dict:
        url = urllib.parse.urlunsplit(
            ("https", self.base, query.format(*args), None, None)
        )

        logging.debug(
            f'\n{method} {url}\n{json.dumps(kwargs.get("json"), sort_keys=True, indent=4)}'
        )

        if self.auth == "basic":
            auth_string = f"{self.user}:{self.api_token}"
            base64_auth_string = base64.b64encode(auth_string.encode()).decode()
            headers = {"Authorization": f"Basic {base64_auth_string}"}
        else:
            headers = {"Authorization": f"Bearer {self.api_token}"}

        try:
            response = requests.request(
                method,
                url,
                headers=headers,
                **kwargs,
            )
            response.raise_for_status()
            logging.debug(
                f'\n{json.dumps(response.json(), sort_keys=True, indent=4)}\n{method} {url}\n{json.dumps(kwargs.get("json"), sort_keys=True, indent=4)}'
            )

        except requests.exceptions.HTTPError:
            self.logger.error(f"HTTP error {response.status_code}: {response.text}")
            raise
        except requests.exceptions.RequestException as ex:
            self.logger.error(f"Request error: {ex}")
            raise
        return response.json() if response.status_code // 100 == 2 else {}

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

    def get_active_epics(self) -> list[dict]:
        jql = f"issuetype = Epic AND project = {self.project}"
        query_params = {
            "jql": jql,
            "fields": "key,summary",
            "maxResults": 100,  # Adjust this as needed
        }
        response = self._api_request("GET", "/rest/api/2/search", params=query_params)
        return response.get("issues", [])

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
        sprint_position: SprintPosition,
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

        body["fields"].update({"priority": {"name": self.priority}})

        if issue_type != "Epic":
            if sprint_position == SprintPosition.NEXT_SPRINT:
                next_sprint = self._get_next_sprint(self.board_id)
                if next_sprint:
                    body["fields"].update({self.sprint_field: next_sprint})

        for field, value in self.custom_fields.items():
            body["fields"].update({field: value})

        return self._api_request("POST", "/rest/api/2/issue", json=body)
