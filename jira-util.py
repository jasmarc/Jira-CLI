import argparse
import configparser
import json
import os
import re
import sys

from jira import JiraAPI

REGULAR_ISSUE_TYPES = ["Story", "Task", "Spike", "Bug"]

SCRIPT_CONFIG = os.path.join(os.path.dirname(__file__), ".jira-util.config")


def read_script_config(config_file):
    c = configparser.ConfigParser()
    c.read(config_file)
    return c


def parse_script_arguments():
    parser = argparse.ArgumentParser(
        description="""CLI for interacting with Jira.

If specifying a file, the file should be in the following format:

# Comment
Deliverable: Lorem ipsum dolor sit amet, consectetur
    Epic: adipiscing elit. Nam eu congue erat.
        Story: Curabitur venenatis tristique diam.
        Story: Phasellus at libero placerat, ornare urna
        Story: eget, blandit lectus. Vestibulum id diam
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-f",
        "--filename",
        type=argparse.FileType("r"),
        help="name of file containing ticket info",
    )
    parser.add_argument(
        "-j",
        "--get-ticket-json",
        metavar="MAR-123",
        type=str,
        dest="get_ticket",
        help="return the ticket info as json",
    )
    parser.add_argument(
        "-c",
        "--create-ticket",
        metavar="Summary",
        type=str,
        dest="create_ticket",
        help="create a new ticket with the given summary",
    )
    parser.add_argument(
        "-e",
        "--epic",
        metavar="epic",
        default=None,
        type=str,
        dest="epic",
        help="set the epic to file the story under",
    )
    parser.add_argument(
        "-s",
        "--scrum",
        metavar="scrum-team",
        default=None,
        type=str,
        dest="scrum_name",
        help="override the default scrum team from the config",
    )
    parser.add_argument(
        "-p",
        "--project",
        metavar="project",
        default=None,
        type=str,
        dest="project",
        help="override the default project from the config",
    )
    parser.add_argument(
        "-i",
        "--issue-type",
        metavar="issue-type",
        default=None,
        type=str,
        dest="issue_type",
        help="override the default project from the config",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        default=False,
        action="store_true",
        help="display verbose output",
    )
    opt = parser.parse_args()
    if not any([opt.filename, opt.create_ticket, opt.get_ticket]):
        parser.print_help(sys.stderr)
        sys.exit(1)
    return opt


def existing_ticket(summary):
    match = re.match("^[A-Z]+-[0-9]+", summary)
    return match.group() if match else None


def create_ticket(jira_api, summary, issue_type, epic):
    return jira_api.create_ticket(
        summary,
        summary,
        issue_type=issue_type,
        epic=epic if issue_type in REGULAR_ISSUE_TYPES else None,
    )["key"]


def verbose_output(jira_api, summary, ticket_id, issue_type, epic):
    url = f"https://{jira_api.base}/browse/{ticket_id}"

    created_or_found = "Found" if existing_ticket(summary) else "Created"
    if issue_type == "Epic":
        return f"\t{created_or_found} {issue_type} {url}"
    elif issue_type in REGULAR_ISSUE_TYPES:
        return f"\t\t{created_or_found} {issue_type} {url}, epic is {epic}"
    else:
        raise ValueError(f"Unknown issue type {issue_type}")


def create_tickets_from_file(jira_api, input_file, verbose=False):
    epic = None
    for line in input_file:
        line = line.strip()

        if not line or line.startswith("#"):
            continue

        issue_type, summary = line.strip().split(": ")

        ticket_id = existing_ticket(summary) or create_ticket(
            jira_api, summary, issue_type, epic
        )

        if issue_type == "Epic":
            epic = ticket_id
        elif issue_type in REGULAR_ISSUE_TYPES and existing_ticket(summary) and epic:
            jira_api.set_epic(ticket_id, epic)

        if verbose:
            print(verbose_output(jira_api, summary, ticket_id, issue_type, epic))


def main():
    config = read_script_config(SCRIPT_CONFIG)
    options = parse_script_arguments()

    j = JiraAPI(config, config_section="JIRA")

    if options.get_ticket:
        print(json.dumps(j.get_ticket(options.get_ticket), indent=4, sort_keys=True))
    elif options.create_ticket:
        response = j.create_ticket(
            options.create_ticket,
            scrum_name=options.scrum_name,
            project=options.project,
            issue_type=options.issue_type,
            epic=options.epic,
        )
        print(f"https://{j.base}/browse/{response['key']}")
    elif options.filename:
        create_tickets_from_file(j, options.filename, verbose=options.verbose)
    else:
        raise ValueError("Invalid arguments.")


if __name__ == "__main__":
    main()
