import os

import questionary
from jira_util.jira import JiraAPI

CONFIG_FILE = "../.jira-util.config"
CONFIG_FILE_HOME = os.path.expanduser("~/.jira-util.config")



def get_issue_type_choices():
    return ["Story", "Task", "Spike", "Bug"]


def get_sprint_choices():
    return ["next sprint", "top of backlog", "bottom of backlog"]


def create_interactive_ticket(jira_api: JiraAPI):
    print("Interactive Jira Ticket Creation")
    print("===============================")

    active_epics = jira_api.get_active_epics()
    choices = [f"{epic['key']} {epic['fields']['summary']}" for epic in active_epics]
    selected_epic_choice = questionary.select(
        "Select an Epic:", choices=choices
    ).ask()

    selected_epic = selected_epic_choice.split()[0]

    issue_type_choices = get_issue_type_choices()
    selected_issue_type = questionary.select(
        "Select an Issue Type:", choices=issue_type_choices
    ).ask()

    sprint_choices = get_sprint_choices()
    selected_sprint = questionary.select(
        "Select a Sprint (Location):", choices=sprint_choices
    ).ask()

    title = questionary.text("Enter Title:").ask()

    # Use title as description for simplicity
    description = title

    jira_api.create_ticket(title, description, issue_type=selected_issue_type, epic=selected_epic, sprint=selected_sprint)

    print("Ticket created successfully!")


if __name__ == "__main__":
    # Create a JiraAPI instance using appropriate configuration
    config = ...  # Load configuration as needed
    j = JiraAPI(config, config_section="RON")

    # Call the interactive function to create a ticket
    create_interactive_ticket(j)
