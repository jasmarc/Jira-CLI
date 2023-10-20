from __future__ import annotations

import base64
import configparser
import json
import logging
import urllib
import urllib.parse
from enum import Enum
from typing import Any

import requests
from requests import codes


class IssueType(Enum):
    STORY = "Story"
    TASK = "Task"
    SPIKE = "Spike"
    BUG = "Bug"

    @classmethod
    def is_valid(cls, input_string: str) -> bool:
        """
        Indicates whether the given string is a valid enum value
        @param input_string:
        @return: True if the given string is a valid enum value
        """
        return input_string in cls.__members__


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
        self.project = config.get(config_section, "PROJECT")
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
        def _parse_params(params):
            if not params:
                return None
            param_list = [f"{key}={value}" for key, value in params.items()]
            params_string = "?" + "&".join(param_list)
            return params_string

        def _parse_response(r):
            try:
                if r.ok and r.status_code != codes.NO_CONTENT:
                    return r.json()
                else:
                    return {}
            except ValueError:
                return {}

        url = urllib.parse.urlunsplit(
            ("https", self.base, query.format(*args), None, None)
        )

        logging.debug(
            f'\n{method} {url}{_parse_params(kwargs.get("params"))}\n{json.dumps(kwargs.get("json"), sort_keys=True, indent=4)}'
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
            response_json = _parse_response(response)
            logging.debug(
                f'\n{json.dumps(response_json, sort_keys=True, indent=4)}\n{method} {url}\n{json.dumps(kwargs.get("json"), sort_keys=True, indent=4)}'
            )

        except requests.exceptions.HTTPError:
            self.logger.error(f"HTTP error {response.status_code}: {response.text}")
            raise
        except requests.exceptions.RequestException as ex:
            self.logger.error(f"Request error: {ex}")
            raise
        return response_json

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
        # Initialize an empty list to store JQL clauses
        jql_clauses = []

        # Iterate over the dictionary items and format them as JQL clauses
        for field, value in self.custom_fields.items():
            field_name = field.replace("customfield_", "")
            if isinstance(value, dict):
                # Handle dictionary values
                value_str = ", ".join([f"'{v}'" for _, v in value.items()])
                jql_clause = f"cf[{field_name}] = {value_str}"
            else:
                # Handle non-dictionary values
                jql_clause = f"cf[{field_name}] ~ '{value}'"
            jql_clauses.append(jql_clause)

        # Join the JQL clauses with ' OR ' to create the final JQL query
        jql_query = " OR ".join(jql_clauses)

        jql = (
            f"issuetype = Epic "
            f"AND project = {self.project} "
            f"AND ({jql_query}) "
            f"AND status = 'In Progress' "
            f"ORDER BY summary ASC"
        )

        logging.debug({"jql": jql})
        query_params = {
            "jql": jql,
            "fields": "key,summary",
            "maxResults": 100,
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

    def _move_issue_to_backlog_position(
            self, issue_key: str, position: SprintPosition
    ) -> None:
        data = {'issues': [issue_key]}

        if position == SprintPosition.BOTTOM_OF_BACKLOG:
            params = {"rankAfterIssue": "last"}
        elif position == SprintPosition.TOP_OF_BACKLOG:
            params = {"rankBeforeIssue": "first"}

        self._api_request("POST", "/rest/agile/1.0/backlog/issue", json=data, params=params)

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

        created_issue = self._api_request("POST", "/rest/api/2/issue", json=body)

        if created_issue and sprint_position in (
            SprintPosition.TOP_OF_BACKLOG,
            SprintPosition.BOTTOM_OF_BACKLOG,
        ):
            self._move_issue_to_backlog_position(created_issue["key"], sprint_position)

        return created_issue
