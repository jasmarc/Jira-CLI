import configparser
import unittest

from jira import JiraAPI


class TestJiraAPI(unittest.TestCase):
    def setUp(self):
        # Load config from INI for testing
        config = configparser.ConfigParser()
        config.read(".jira-util.config")

        # Initialize JiraAPI instance with test config
        self.jira_api = JiraAPI(config)

    def test_config_values(self):
        self.assertEqual(self.jira_api.base, "jira.kdc.foo.com")
        self.assertEqual(self.jira_api.project, "PROJ")
        self.assertEqual(self.jira_api.user, "username")
        self.assertEqual(self.jira_api.api_token, "token")
        self.assertEqual(self.jira_api.epic_field, "customfield_123456")
        self.assertEqual(self.jira_api.epic_name_field, "customfield_45612")
        self.assertEqual(self.jira_api.sprint_field, "customfield_678910")
        self.assertEqual(self.jira_api.board_id, "12345")
        self.assertEqual(self.jira_api.priority, "Awaiting Priority")

    def test_custom_fields(self):
        custom_fields = self.jira_api.custom_fields
        self.assertEqual(len(custom_fields), 3)  # Ensure there are two custom fields

        expected_custom_fields = {
            "customfield_12345": "foo",
            "customfield_13455": "bar",
            "customfield_13456": "baz",
        }

        for expected_field in expected_custom_fields:
            self.assertIn(expected_field, custom_fields)


if __name__ == "__main__":
    unittest.main()
