from __future__ import annotations

import base64
import json
import logging
import unittest
from configparser import ConfigParser
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import requests
import requests_mock
from parameterized import parameterized

from jira_util.jira import JiraAPI, SprintPosition


class TestJiraAPI(unittest.TestCase):
    def setUp(self) -> None:
        config_file_path = Path(__file__).parent / ".." / ".jira-util.config.template"
        logging.info(config_file_path)
        self.jira_config = ConfigParser()
        self.jira_config.read(config_file_path)
        self.jira_api = JiraAPI(self.jira_config, config_section="JIRA")

    @requests_mock.mock()
    def test_api_request_successful(self, mock_request: requests_mock.Mocker) -> None:
        query = "/rest/api/2/issue/{}"
        ticket = "JIRA-123"
        url = f"https://example.com{query.format(ticket)}"
        method = "GET"
        response_data = {"key": "JIRA-123"}
        response_json = json.dumps(response_data)

        mock_request.get(url, text=response_json, status_code=200)
        result = self.jira_api._api_request(method, query, ticket)

        self.assertEqual(result, response_data)

    @requests_mock.mock()
    def test_api_request_failed(self, mock_request: requests_mock.Mocker) -> None:
        query = "/rest/api/2/issue/{}"
        ticket = "JIRA-123"
        url = f"https://example.com{query.format(ticket)}"
        method = "GET"
        error_message = "Connection error"

        mock_request.get(url, exc=requests.exceptions.RequestException(error_message))

        mock_logger = MagicMock()
        self.jira_api.logger = mock_logger

        with self.assertRaises(requests.exceptions.RequestException) as context:
            self.jira_api._api_request(method, query, ticket)

        self.assertEqual(str(context.exception), error_message)
        mock_logger.error.assert_called_with(f"Request error: {error_message}")

    @parameterized.expand(
        [
            ("JIRA-123", 200, {"key": "JIRA-123"}),
            ("JIRA-456", 404, None),
        ]
    )
    @requests_mock.mock()
    def test_get_ticket(
        self,
        ticket: str,
        status_code: int,
        response_json: dict | None,
        mock_request: requests_mock.Mocker,
    ) -> None:
        mock_request.get(
            f"https://example.com/rest/api/2/issue/{ticket}",
            status_code=status_code,
            json=response_json,
        )

        try:
            result = self.jira_api.get_ticket(ticket)
        except requests.exceptions.HTTPError as ex:
            response = ex.response
            assert response is not None
            self.assertEqual(response.status_code, status_code)
            if status_code == 404:
                self.assertIn("404 Client Error: None", str(ex))

            return

        if status_code == 200:
            expected_response_data = response_json
        else:
            expected_response_data = {}

        self.assertEqual(result, expected_response_data)

    @parameterized.expand(
        [
            ("JIRA-123", "A comment", 201, {"id": 1}),
        ]
    )
    @requests_mock.mock()
    def test_add_comment(
        self,
        ticket: str,
        comment: str,
        status_code: int,
        response_json: dict,
        mock_request: requests_mock.Mocker,
    ) -> None:
        mock_request.post(
            f"https://example.com/rest/api/2/issue/{ticket}/comment",
            status_code=status_code,
            json=response_json,
        )

        result = self.jira_api.add_comment(ticket, comment)

        self.assertEqual(result, response_json)

    @parameterized.expand(
        [
            ("JIRA-123", 200, {"key": "JIRA-123"}),
        ]
    )
    @requests_mock.mock()
    def test_get_comment(
        self,
        ticket: str,
        status_code: int,
        response_json: dict,
        mock_request: requests_mock.Mocker,
    ) -> None:
        mock_request.get(
            f"https://example.com/rest/api/2/issue/{ticket}/comment",
            status_code=status_code,
            json=response_json,
        )

        result = self.jira_api.get_comment(ticket)

        self.assertEqual(result, response_json)

    @parameterized.expand(
        [
            ("basic", "test_user@example.com", "test_api_token", "Basic"),
            ("bearer", "test_user@example.com", "test_api_token", "Bearer"),
        ]
    )
    @requests_mock.mock()
    def test_create_ticket_authorization(
        self,
        auth_type: str,
        user: str,
        api_token: str,
        expected_auth_type: str,
        mock_request: requests_mock.Mocker,
    ) -> None:
        title = "Title1"
        description = "Description"
        issue_type = "Story"
        epic = None
        project = None
        sprint_position = SprintPosition.NEXT_SPRINT
        status_code = 200
        response_json = {"key": "JIRA-123"}

        mock_request.get(
            "https://example.com/rest/agile/1.0/board/999/sprint?state=future",
            status_code=200,
            json={"values": [{"id": "123"}]},
        )

        mock_request.post(
            "https://example.com/rest/api/2/issue",
            status_code=status_code,
            json=response_json,
        )

        self.jira_api.auth = auth_type
        self.jira_api.user = user
        self.jira_api.api_token = api_token

        result = self.jira_api.create_ticket(
            title, description, issue_type, epic, project, sprint_position
        )

        self.assertEqual(result, response_json)

        if expected_auth_type == "Basic":
            base64_auth_string = base64.b64encode(
                f"{user}:{api_token}".encode()
            ).decode()
            expected_authorization_header = f"{expected_auth_type} {base64_auth_string}"
        else:
            expected_authorization_header = f"{expected_auth_type} {api_token}"
        self.assertEqual(
            mock_request.last_request.headers["Authorization"],
            expected_authorization_header,
        )

    @parameterized.expand(
        [
            (
                "Title1",
                "Description",
                "Story",
                "EPIC-123",
                None,
                SprintPosition.NEXT_SPRINT,
                200,
                {
                    "key": "JIRA-123",
                    "fields": {
                        "customfield_12345": "EPIC-123",
                    },
                },
                "Bearer",
            ),
            (
                "Title4",
                "Description",
                "Epic",
                None,
                None,
                SprintPosition.NEXT_SPRINT,
                200,
                {
                    "key": "JIRA-124",
                    "fields": {
                        "customfield_54321": "Title4",
                    },
                },
                "Bearer",
            ),
        ]
    )
    @requests_mock.mock()
    def test_create_ticket_200(
        self,
        title: str,
        description: str,
        issue_type: str,
        epic: str | None,
        project: str | None,
        sprint_position: SprintPosition,
        status_code: int,
        response_json: dict | None,
        expected_auth_type: str,  # Add this parameter to the test case
        mock_request: requests_mock.Mocker,
    ) -> None:
        mock_request.get(
            "https://example.com/rest/agile/1.0/board/999/sprint?state=future",
            status_code=200,
            json={"values": [{"id": "123"}]},
        )

        mock_request.post(
            "https://example.com/rest/api/2/issue",
            status_code=status_code,
            json=response_json,
        )

        self.jira_api.auth = expected_auth_type

        result = self.jira_api.create_ticket(
            title, description, issue_type, epic, project, sprint_position
        )

        self.assertEqual(result, response_json)

        expected_authorization_header = f"{expected_auth_type} test_api_token"  # Assuming the test case is using Bearer auth
        self.assertEqual(
            mock_request.last_request.headers["Authorization"],
            expected_authorization_header,
        )

        if issue_type == "Epic":
            self.assertEqual(
                result["fields"][self.jira_api.epic_name_field], title
            )  # Check that the epic name field is updated
        elif issue_type == "Story":
            self.assertNotIn(self.jira_api.epic_name_field, result.get("fields", {}))

        if epic:
            self.assertEqual(
                result["fields"][self.jira_api.epic_field], epic
            )  # Check that the epic field is updated

    @parameterized.expand(
        [
            (
                "Title2",
                "Description",
                "Story",
                None,
                None,
                SprintPosition.NEXT_SPRINT,
                400,
                {"errorMessages": ["Invalid input"]},
                requests.exceptions.HTTPError(
                    'HTTP error 400 Client Error: {"errorMessages": ["Invalid input"]}'
                ),
                'HTTP error 400: {"errorMessages": ["Invalid input"]}',
            ),
            (
                "Title3",
                "Description",
                "Story",
                None,
                None,
                SprintPosition.NEXT_SPRINT,
                500,
                None,
                requests.exceptions.RequestException("Connection error"),
                "HTTP error 500: ",
            ),
        ]
    )
    @requests_mock.mock()
    def test_create_ticket_non_200(
        self,
        title: str,
        description: str,
        issue_type: str,
        epic: str | None,
        project: str | None,
        sprint_position: SprintPosition,
        status_code: int,
        response_json: dict | None,
        exception_to_raise: Exception | None,
        exception_message: str,
        mock_request: requests_mock.Mocker,
    ) -> None:
        mock_request.get(
            "https://example.com/rest/agile/1.0/board/999/sprint?state=future",
            status_code=200,
            json={"values": [{"id": "123"}]},
        )

        mock_request.post(
            "https://example.com/rest/api/2/issue",
            status_code=status_code,
            json=response_json,
        )

        with self.assertLogs("jira_util", level=logging.ERROR) as cm:
            with self.assertRaises(
                requests.exceptions.RequestException
                if exception_to_raise
                else requests.exceptions.HTTPError
            ) as context:
                self.jira_api.create_ticket(
                    title, description, issue_type, epic, project, sprint_position
                )

        if exception_to_raise:
            self.assertIn(f"ERROR:jira_util.jira:{exception_message}", cm.output[0])

        exception = context.exception
        response = exception.response
        assert response is not None
        self.assertEqual(response.status_code, status_code)
        try:
            # Try to parse the response as JSON
            got_response_json = response.json()
        except ValueError:
            got_response_json = None

            # Verify the parsed JSON or response content if parsing failed
        self.assertEqual(got_response_json, response_json)

    @parameterized.expand(
        [
            ("JIRA-123", "EPIC-456", 200, {"key": "JIRA-123"}),
            ("JIRA-789", "EPIC-123", 404, None),
        ]
    )
    @requests_mock.mock()
    def test_set_epic(
        self,
        ticket: str,
        parent_epic: str,
        status_code: int,
        response_json: dict | None,
        mock_request: requests_mock.Mocker,
    ) -> None:
        mock_request.put(
            f"https://example.com/rest/api/2/issue/{ticket}",
            status_code=status_code,
            json=response_json,
        )

        expected_json = {"fields": {self.jira_api.epic_field: parent_epic}}

        mock_api_request = Mock(return_value=response_json)
        if status_code == 404:
            exception = requests.exceptions.HTTPError(
                'HTTP error 404: {"errorMessages": ["Not Found"]}'
            )
            mock_api_request.side_effect = exception

        with patch.object(self.jira_api, "_api_request", new=mock_api_request):
            if status_code == 404:
                with self.assertRaises(requests.exceptions.HTTPError) as context:
                    self.jira_api.set_epic(ticket, parent_epic)

                self.assertEqual(str(context.exception), str(exception))
            else:
                result = self.jira_api.set_epic(ticket, parent_epic)
                if status_code == 200:
                    self.assertEqual(result, response_json)
                else:
                    self.assertEqual(result, {})

        if status_code != 404:
            mock_api_request.assert_called_once_with(
                "PUT", "/rest/api/2/issue/{}", ticket, json=expected_json
            )

    @parameterized.expand(
        [
            ("base", "example.com"),
            ("project", "TEST"),
            ("user", "test_user@example.com"),
            ("api_token", "test_api_token"),
            ("epic_field", "customfield_12345"),
            ("epic_name_field", "customfield_54321"),
            ("sprint_field", "customfield_67890"),
            ("board_id", "999"),
            ("priority", "Medium"),
        ]
    )
    def test_config_values(self, config_key: str, expected_value: str) -> None:
        self.assertEqual(getattr(self.jira_api, config_key), expected_value)

    @parameterized.expand(
        [
            ("customfield_11111", "CustomValue1"),
            ("customfield_22222", {"accountId": "123456:abcdef123"}),
            ("customfield_33333", {"value": "CustomValue2"}),
        ]
    )
    def test_custom_fields(self, field: str, expected_value: str) -> None:
        custom_fields: dict[str, str] = self.jira_api.custom_fields
        self.assertIn(field, custom_fields)
        self.assertEqual(custom_fields[field], expected_value)


if __name__ == "__main__":
    unittest.main()
