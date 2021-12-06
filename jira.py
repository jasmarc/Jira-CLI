import json
import urllib

import requests


class JiraAPI(object):
    """
    Utility for interacting with the Jira API
    See https://docs.atlassian.com/software/jira/docs/api/REST/8.5.13/
    """

    def __init__(self, config, config_section='JIRA'):
        super(JiraAPI, self).__init__()
        self.base = config.get(config_section, 'BASE_URL')
        self.project = config.get(config_section, 'PROJECT', fallback='MAR')
        self.user = config.get(config_section, 'USER')
        self.api_token = config.get(config_section, 'API_TOKEN')
        self.scrum_name = config.get(config_section, 'SCRUM_NAME', fallback=None)
        self.scrum_field = config.get(config_section, 'SCRUM_FIELD')
        self.epic_field = config.get(config_section, 'EPIC_FIELD')
        self.epic_name_field = config.get(config_section, 'EPIC_NAME_FIELD')

    def _api_request(self, method, query, *args, **kwargs):
        url = urllib.parse.urlunsplit(('https', self.base, query.format(*args), None, None))
        try:
            r = requests.request(method, url, auth=(self.user, self.api_token), **kwargs)
            # print(f'\n{r.json()}\n{method} {url}\n{json.dumps(kwargs.get("json"), sort_keys=True, indent=4)}')
            r.raise_for_status()
        except Exception as ex:
            msg = f'Check your VPN connection and that user and api token are specified in the config'
            msg += f'\n{r.text}\n{method} {url}\n{json.dumps(kwargs.get("json"), sort_keys=True, indent=4)}'
            raise Exception(msg) from ex
        return r.json() if r.text else None

    def get_comment(self, ticket):
        return self._api_request('GET', '/rest/api/2/issue/{}/comment', ticket)

    def add_comment(self, ticket, comment):
        return self._api_request('POST', '/rest/api/2/issue/{}/comment', ticket, json={"body": comment})

    def get_ticket(self, ticket):
        return self._api_request('GET', '/rest/api/2/issue/{}', ticket)

    def _get_sprint(self, board_id):
        return self._api_request('GET', 'rest/agile/1.0/board/{}/sprint?state=future', board_id)

    def _get_next_sprint(self, board_id):
        return self._get_sprint(board_id)['values'][0]['id']

    def _set_parent(self, parent):
        return {'issuelinks': [{
            'add': {
                'type': {'name': 'Initiative', 'inward': 'Parent of', 'outward': 'Child of'},
                'inwardIssue': {'key': parent}
            }
        }]}

    def set_parent(self, ticket, parent):
        return self._api_request('PUT', '/rest/api/2/issue/{}', ticket, json={'update': self._set_parent(parent)})

    def set_epic(self, ticket, parent_epic):
        return self._api_request('PUT', '/rest/api/2/issue/{}', ticket, json={'fields': {self.epic_field: parent_epic}})

    def create_ticket(self, title, description=None, issue_type=None, epic=None, parent=None,
                      scrum_name=None, project=None):
        body = {'fields': {
            'project': {'key': project or self.project},
            'summary': title,
            'description': description or title,
            'issuetype': {'name': issue_type or 'Story'}
        }}

        if issue_type == 'Epic':
            body['fields'].update({self.epic_name_field: title})

        if (scrum_name or self.scrum_name) and scrum_name != 'None':
            body['fields'].update({self.scrum_field: [scrum_name or self.scrum_name]})

        if epic:
            body['fields'].update({self.epic_field: epic})

        if parent:
            body['update'] = self._set_parent(parent)

        body['fields'].update({'priority': {'name': 'P3'}})
        body['fields'].update({'customfield_10200': self._get_next_sprint(1530)})

        return self._api_request('POST', '/rest/api/2/issue', json=body)
