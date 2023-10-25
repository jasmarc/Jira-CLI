from __future__ import annotations

import argparse
import configparser
import json
import logging
import re
import sys
if sys.version_info >= (3, 8):
    from importlib import metadata
else:
    import importlib_metadata as metadata
from pathlib import Path

from jira_util.generate_config import CONFIG_FILE_HOME
from jira_util.interactive import create_interactive_ticket
from jira_util.jira import IssueType, JiraAPI, SprintPosition


def read_script_config(config_file: Path) -> configparser.ConfigParser:
    c = configparser.ConfigParser()
    c.read(config_file)
    return c


def parse_script_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="""CLI for interacting with Jira.

If specifying a file, the file should be in the following format:

# Comment
Deliverable: Lorem ipsum dolor sit amet, consectetur
    Epic: adipiscing elit. Name eu congue erat.
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
        "--env",
        dest="config_section",
        default="JIRA",
        help="Specify the environment to use for configuration",
    )
    parser.add_argument(
        "--interactive",
        default=False,
        action="store_true",
        help="create a Jira ticket interactively",
    )
    parser.add_argument(
        "-d",
        "--debug",
        default=False,
        action="store_true",
        help="Enable DEBUG log level (default is INFO)",
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="Print the version and exit",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        default=False,
        action="store_true",
        help="display verbose output",
    )
    opt = parser.parse_args()
    if opt.version:
        version = metadata.version('jira_util')
        print(f"jira-util version {version}")
        sys.exit(0)
    if not any([opt.filename, opt.create_ticket, opt.get_ticket, opt.interactive]):
        parser.print_help(sys.stderr)
        sys.exit(1)
    return opt


def existing_ticket(summary: str) -> str | None:
    match = re.match("^[A-Z]+-[0-9]+", summary)
    return match.group() if match else None


def create_ticket(
    jira_api: JiraAPI,
    summary: str,
    issue_type: str,
    epic: str | None,
    project: str | None,
) -> str:
    return jira_api.create_ticket(
        summary,
        summary,
        issue_type=issue_type,
        epic=epic if issue_type in IssueType else None,
        project=project,
        sprint_position=SprintPosition.NEXT_SPRINT,
    )["key"]


def verbose_output(
    jira_api: JiraAPI, summary: str, ticket_id: str, issue_type: str, epic: str | None
) -> str:
    url = f"https://{jira_api.base}/browse/{ticket_id}"
    created_or_found = "Found" if existing_ticket(summary) else "Created"
    if issue_type == "Epic":
        return f"\t{created_or_found} {issue_type} {url}"
    elif IssueType.is_valid(issue_type):
        return f"\t\t{created_or_found} {issue_type} {url}, epic is {epic}"
    else:
        raise ValueError(f"Unknown issue type {issue_type}")


def create_tickets_from_file(
    jira_api: JiraAPI,
    input_file: str,
    verbose: bool = False,
    project: str | None = None,
) -> None:
    epic = None
    for line in input_file:
        line = line.strip()

        if not line or line.startswith("#"):
            continue

        issue_type, summary = line.strip().split(": ")

        ticket_id = existing_ticket(summary) or create_ticket(
            jira_api, summary, issue_type, epic, project
        )

        if issue_type == "Epic":
            epic = ticket_id
        elif IssueType.is_valid(issue_type) and existing_ticket(summary) and epic:
            jira_api.set_epic(ticket_id, epic)

        if verbose:
            print(verbose_output(jira_api, summary, ticket_id, issue_type, epic))


def main() -> None:
    options = parse_script_arguments()
    logging.basicConfig(level=logging.DEBUG if options.debug else logging.INFO)

    config = read_script_config(CONFIG_FILE_HOME)
    logging.debug(CONFIG_FILE_HOME)

    j = JiraAPI(config, config_section=options.config_section)

    if options.get_ticket:
        print(json.dumps(j.get_ticket(options.get_ticket), indent=4, sort_keys=True))
    elif options.interactive:
        response = create_interactive_ticket(j, options.project)
        print(f"https://{j.base}/browse/{response['key']}")
    elif options.create_ticket:
        response = j.create_ticket(
            options.create_ticket,
            options.create_ticket,
            project=options.project,
            issue_type=options.issue_type,
            epic=options.epic,
            sprint_position=SprintPosition.NEXT_SPRINT,
        )
        print(f"https://{j.base}/browse/{response['key']}")
    elif options.filename:
        create_tickets_from_file(j, options.filename, verbose=options.verbose)
    else:
        raise ValueError("Invalid arguments.")


if __name__ == "__main__":
    main()
