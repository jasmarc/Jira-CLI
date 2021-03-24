# jira-util

Utility for programmatic interaction with Jira.

```
usage: jira-util.py [-h] [-f FILENAME] [-j MAR-123] [-v]

CLI for interacting with Jira.

If specifying a file, the file should be in the following format:

# Comment
Deliverable: Lorem ipsum dolor sit amet, consectetur
    Epic: adipiscing elit. Nam eu congue erat.
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

* run `brew install pyenv-virtualenv` (see [here](https://github.com/pyenv/pyenv-virtualenv#installing-with-homebrew-for-macos-users) for more details)
* add these lines to your bash or zsh profile

  ```
  eval "$(pyenv init -)"
  eval "$(pyenv virtualenv-init -)"
  ```

* run `pyenv install 3.9.0`
* run `pyenv activate jira-util-3.9.0`
* run `pip install -r requirements.txt`
* copy `.jira-util.config.template` to `.jira-util.config`
* fill out the `USER` and `API_TOKEN` fields (see [here](https://support.atlassian.com/atlassian-account/docs/manage-api-tokens-for-your-atlassian-account/) for more details).

## Usage

### Reading a single Jira ticket

This will dump the Jira ticket as a JSON blob:

```
python jira-util.py -j MAR-7335
```

### Creating tickets from a file

Example input file:

```
# Comment
Deliverable: Lorem ipsum dolor sit amet, consectetur
    Epic: adipiscing elit. Nam eu congue erat.
        Story: Curabitur venenatis tristique diam.
        Story: Phasellus at libero placerat, ornare urna
        Story: eget, blandit lectus. Vestibulum id diam
```

Given a file in this format you may invoke ticket creation as follows:

```
python jira-util.py -v -f example-input.txt 
```

**Notes:**

 - Each line should be of the format `issue_type, summary`
 - Valid issues types are `Deliverable`, `Epic`, `Story`
 - Comments, denoted by `#`, and empty lines will be skipped
 - Leading whitespace is ignored
 - Stories followed by Epics will be linked to the Epics they follow
 - Epics followed by Deliverables will be linked to the Deliverables they follow