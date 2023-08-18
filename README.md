# jira-util

Utility for programmatic interaction with Jira.

```shell
usage: jira-util.py [-h] [-f FILENAME] [-j MAR-123] [-v]

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
  -j MAR-123, --get-ticket-json MAR-123
                        return the ticket info as json
  -v, --verbose         display verbose output
```

## Getting Started

- Install `pipenv` if you haven't already:

  ```shell
  pip install pipenv
  ```

- Navigate to the project directory in your terminal.

- Create a virtual environment and install dependencies using `pipenv`:

  ```shell
  pipenv install --dev
  ```

- Copy `.jira-util.config.template` to `.jira-util.config` and open it:

  ```shell
  cp .jira-util.config.template .jira-util.config
  ```

- Fill out the `USER` and `API_TOKEN` fields in `.jira-util.config`
  (see [here](https://support.atlassian.com/atlassian-account/docs/manage-api-tokens-for-your-atlassian-account/)
  for more details).

- Run tests and other tasks using `pipenv`:

  ```shell
  pipenv run make test
  # ... other commands ...
  ```

- When you're done, exit the virtual environment:

  ```shell
  exit
  ```

## Usage

### Reading a single Jira ticket

This will dump the Jira ticket as a JSON blob:

```shell
python jira-util.py -j MAR-7335
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
 Epic: MAR-123
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
python jira-util.py -v -f example-input.txt
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
- If a ticket id is specified (e.g. `MAR-123`) instead of a summary, that existing ticket will be used instead
  of creating a new ticket.
