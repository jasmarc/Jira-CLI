import questionary

from jira_util.jira import IssueType, JiraAPI, SprintPosition


def get_issue_type_choices() -> list:
    return [issue_type.value for issue_type in IssueType]


def get_sprint_choices() -> list:
    return [sprint_choice.value for sprint_choice in SprintPosition]


def create_interactive_ticket(jira_api: JiraAPI, project: str) -> dict:
    print("Interactive Jira Ticket Creation")
    print("===============================")

    active_epics = jira_api.get_active_epics()
    choices = [f"{epic['key']} {epic['fields']['summary']}" for epic in active_epics]
    selected_epic_choice = questionary.select("Select an Epic:", choices=choices).ask()

    selected_epic = selected_epic_choice.split()[0]

    issue_type_choices = get_issue_type_choices()
    selected_issue_type = questionary.select(
        "Select an Issue Type:", choices=issue_type_choices
    ).ask()

    sprint_choices = get_sprint_choices()
    selected_sprint = questionary.select(
        "Select a Sprint (Location):", choices=sprint_choices
    ).ask()
    selected_sprint = SprintPosition(selected_sprint)

    title = questionary.text("Enter Title:").ask()

    # Use title as description for simplicity
    description = title

    return jira_api.create_ticket(
        title,
        description,
        issue_type=selected_issue_type,
        epic=selected_epic,
        project=project,
        sprint_position=selected_sprint,
    )
