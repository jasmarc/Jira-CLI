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
            r.raise_for_status()
        except Exception as ex:
            msg = f'Check your VPN connection and that user and api token are specified in the config\n{r.json()}'
            raise Exception(msg) from ex
        return r.json()

    def get_comment(self, ticket):
        return self._api_request('GET', '/rest/api/2/issue/{}/comment', ticket)

    def add_comment(self, ticket, comment):
        return self._api_request('POST', '/rest/api/2/issue/{}/comment', ticket, json={"body": comment})

    def get_ticket(self, ticket):
        return self._api_request('GET', '/rest/api/2/issue/{}', ticket)

    def create_ticket(self, title, description, issue_type='Story', epic=None, parent=None):
        body = {'fields': {
            'project': {'key': self.project},
            'summary': title,
            'description': description,
            'issuetype': {'name': issue_type}
        }}

        if issue_type == 'Epic':
            body['fields'].update({self.epic_name_field: title})

        if self.scrum_name:
            body['fields'].update({self.scrum_field: [self.scrum_name]})

        if epic:
            body['fields'].update({self.epic_field: epic})

        if parent:
            body['update'] = {'issuelinks': [{
                'add': {
                    'type': {'name': 'Initiative', 'inward': 'Parent of', 'outward': 'Child of'},
                    'inwardIssue': {'key': parent}
                }
            }]}

        return self._api_request('POST', '/rest/api/2/issue', json=body)
