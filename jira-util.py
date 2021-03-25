import argparse
import configparser
import json
import os
import re
import sys

from jira import JiraAPI

SCRIPT_CONFIG = os.path.join(os.path.dirname(__file__), '.jira-util.config')


def read_script_config(config_file):
    c = configparser.ConfigParser()
    c.read(config_file)
    return c


def parse_script_arguments():
    parser = argparse.ArgumentParser(description="""CLI for interacting with Jira.

If specifying a file, the file should be in the following format:

# Comment
Deliverable: Lorem ipsum dolor sit amet, consectetur
    Epic: adipiscing elit. Nam eu congue erat.
        Story: Curabitur venenatis tristique diam.
        Story: Phasellus at libero placerat, ornare urna
        Story: eget, blandit lectus. Vestibulum id diam
        """, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("-f", "--filename", type=argparse.FileType('r'), help="name of file containing ticket info")
    parser.add_argument("-j", "--get-ticket-json", metavar='MAR-123', type=str, dest='ticket',
                        help="return the ticket info as json")
    parser.add_argument("-v", "--verbose", default=False, action='store_true', help="display verbose output")
    opt = parser.parse_args()
    if not opt.filename and not opt.ticket:
        parser.print_help(sys.stderr)
        sys.exit(1)
    return opt


def create_tickets_from_file(jira_api, input_file, verbose=False):
    def _existing_ticket():
        match = re.match('^[A-Z]+-[0-9]+', summary)
        return match.group() if match else None

    def _create_ticket():
        return jira_api.create_ticket(summary, summary, issue_type=issue_type,
                                      epic=epic if issue_type == 'Story' else None,
                                      parent=deliverable if issue_type == 'Epic' else None)['key']

    def _verbose_output():
        created_or_found = 'Found' if _existing_ticket() else 'Created'
        return {
            'Deliverable': f'{created_or_found} {issue_type} {ticket_id}',
            'Epic': f'\t{created_or_found} {issue_type} {ticket_id}, parent deliverable is {deliverable}',
            'Story': f'\t\t{created_or_found} {issue_type} {ticket_id}, epic is {epic}',
        }[issue_type]

    deliverable, epic = None, None
    for line in input_file:
        line = line.strip()

        if not line or line.startswith('#'):
            continue

        issue_type, summary = line.strip().split(': ')

        ticket_id = _existing_ticket() or _create_ticket()

        if issue_type == 'Deliverable':
            deliverable = ticket_id
        elif issue_type == 'Epic':
            if _existing_ticket() and deliverable:
                jira_api.set_parent(ticket_id, deliverable)
            epic = ticket_id

        if verbose:
            print(_verbose_output())


def main():
    config = read_script_config(SCRIPT_CONFIG)
    options = parse_script_arguments()

    j = JiraAPI(config, config_section='JIRA')

    if options.ticket:
        print(json.dumps(j.get_ticket(options.ticket), indent=4, sort_keys=True))
    elif options.filename:
        create_tickets_from_file(j, options.filename, verbose=options.verbose)
    else:
        raise Exception('Invalid arguments.')


if __name__ == '__main__':
    main()
