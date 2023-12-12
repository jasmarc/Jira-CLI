# jira-util

Utility for programmatic interaction with Jira.

```shell
usage: jira-util [-h] [-f FILENAME] [-j XXX-123] [-c Summary] [-e epic] [-p project] [-i issue-type] [--env CONFIG_SECTION] [--interactive] [-d] [--version] [-v]

CLI for interacting with Jira.

If specifying a file, the file should be in the following format:

# Comment
Deliverable: Lorem ipsum dolor sit amet, consectetur
    Epic: adipiscing elit. Name eu congue erat.
        Story: Curabitur venenatis tristique diam.
        Story: Phasellus at libero placerat, ornare urna
        Story: eget, blandit lectus. Vestibulum id diam


optional arguments:
  -h, --help            show this help message and exit
  -f FILENAME, --filename FILENAME
                        name of file containing ticket info
  -j XXX-123, --get-ticket-json XXX-123
                        return the ticket info as json
  -c Summary, --create-ticket Summary
                        create a new ticket with the given summary
  -e epic, --epic epic  set the epic to file the story under
  -p project, --project project
                        override the default project from the config
  -i issue-type, --issue-type issue-type
                        override the default project from the config
  --env CONFIG_SECTION  Specify the environment to use for configuration
  --interactive         create a Jira ticket interactively
  -d, --debug           Enable DEBUG log level (default is INFO)
  --version             Print the version and exit
  -v, --verbose         display verbose output

```

## Getting Started

### Install

```
pip install git+https://github.com/jasmarc/Jira-CLI.git
```

### Initialize your config file

```
jira-util --init-config
```

## Usage

### Reading a single Jira ticket

This will dump the Jira ticket as a JSON blob:

```shell
jira-util -j XXX-1234
```

### Create a ticket from CLI

```shell
jira-util --epic XXX-1234 --issue-type Task --create-ticket "Ticket description"  
```

### Create a ticket from CLI Interactively

```shell
jira-util --env DEV --interactive
```

### Creating tickets from a file

Example input file:

```text
# Lines with `#` are skipped as comments
Deliverable: Lorem ipsum dolor sit amet, consectetur
 Epic: adipiscing elit. Name eu congue erat.
  Story: Curabitur venenatis tristique diam.
  Story: Phasellus at libero placerat, ornare urna
  Story: eget, blandit lectus. Vestibulum id diam
 # Epic already exists
 Epic: XXX-123
  Story: Quisque pulvinar erat eget diam fermentum, vel
  Story: bibendum erat rhoncus. Phasellus mauris enim,
# Deliverable already exists
Deliverable: MAR-234
 Epic: Suspendisse viverra vulputate urna, id molestie
  Story: quam facilisis sit amet. Etiam non viverra
  Story: sapien. Phasellus non lectus non lectus
```

Given a file in this format you may invoke ticket creation as follows:

```shell
jira-util -v -f example-input.txt
```

**Notes:**

- Each line should be of the format `issue_type, summary`.
- Valid issues types are `Deliverable`, `Epic`, `Story`.
- Comments, denoted by `#`, and empty lines will be skipped.
- Leading whitespace is ignored.
- Stories followed by Epics will be linked to the Epics they follow,
- Epics followed by Deliverables will be linked to the Deliverables they follow.
- If only Stories are present they will be orphaned and not associated with an Epic or Deliverable.
- If only Stories and Epics are present the stories will be linked to the Epic(s) but not associated with a
  Deliverable.
- If a ticket id is specified (e.g. `XXX-123`) instead of a summary, that existing ticket will be used instead
  of creating a new ticket.
