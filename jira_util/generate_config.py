from __future__ import annotations

import configparser
import json
import os
from pathlib import Path
from urllib.parse import urlparse

import questionary

CONFIG_FILE_HOME = Path.home() / ".jira-util.config"


def read_config(config_file: Path) -> configparser.ConfigParser:
    c = configparser.ConfigParser()
    c.read(config_file)
    return c


def validate_base_url(url: str) -> str | bool:
    if not urlparse(url).netloc and not urlparse(f"https://{url}").netloc:
        return "Please enter a valid URL"

    return True


def validate_custom_field_id(field_id: str) -> str | bool:
    if not field_id.startswith("customfield_"):
        return "Custom field ID must start with 'customfield_'"

    return True  # Validation passed


def validate_board_id(board_id: str) -> str | bool:
    if not board_id.isdigit():
        return "board_id should be integer"

    return True


def get_base_url(default: str | None = None) -> str:
    return questionary.text("Base URL:", default=default).ask().strip().rstrip("/")


def get_api_token(default: str | None = None) -> str:
    api_token_info = (
        "You can create an API token by following the instructions here:\n"
        "https://support.atlassian.com/atlassian-account/docs/manage-api-tokens-for-your-atlassian-account/"
    )
    print(api_token_info)

    api_token = questionary.password("API Token:", default=default).ask()
    return api_token


def get_custom_fields() -> dict:
    custom_fields = {}
    while True:
        field_name = questionary.text(
            "Custom Field Name (e.g., customfield_12345):"
        ).ask()
        field_value = questionary.text(
            "Custom Field Value or JSON (press Enter if not applicable):"
        ).ask()

        if not field_value:
            break

        if field_value.startswith("{") and field_value.endswith("}"):
            try:
                field_value = json.loads(field_value)
            except json.JSONDecodeError:
                print("Invalid JSON format. Please provide valid JSON or a value.")
                continue

        custom_fields[field_name] = field_value

        add_another = questionary.confirm("Add another custom field?").ask()
        if not add_another:
            break

    return custom_fields


def get_existing_values(section: configparser.SectionProxy) -> dict:
    defaults = {}
    for option in section:
        value = section[option]
        if option == "CUSTOM_FIELDS":
            defaults[option] = json.loads(value)
        else:
            defaults[option] = value
    return defaults


def ask_new_section_name(existing_sections: list[str]) -> str:
    section_choice = ["Add a new section"]
    section_choice.extend(existing_sections)
    default_choice = section_choice[0]
    section_menu = questionary.select(
        "Choose an existing section or add a new one:",
        choices=section_choice,
        default=default_choice,
    ).ask()

    if section_menu == "Add a new section":
        return questionary.text("Please provide a name for the new section:").ask()
    else:
        return section_menu


def main() -> configparser.ConfigParser:
    print("Welcome to the Jira Configuration Generator!")
    print(
        "This script will help you create a new configuration section for your Jira settings."
    )

    print(f"Your config file will be written to: {os.path.abspath(CONFIG_FILE_HOME)}")

    config = read_config(CONFIG_FILE_HOME)

    new_section_name = ask_new_section_name(config.sections())

    if new_section_name not in config.sections():
        config.add_section(new_section_name)
    else:
        use_existing = questionary.confirm(
            f"Section '{new_section_name}' already exists. Do you want to use existing values?"
        ).ask()
        if use_existing:
            print(f"Using existing values for section '{new_section_name}'")
            defaults = get_existing_values(config[new_section_name])
        else:
            print("Aborting...")
            exit(1)
    defaults = defaults if "defaults" in locals() else {}

    print(
        f"\nI'm going to help you fill in the '{new_section_name}' section of your Jira config.\n"
    )

    config.set(
        new_section_name,
        "USER",
        questionary.text(
            "User name (e.g., your_email@example.com):",
            default=defaults.get("USER", "") if defaults else "",
        ).ask(),
    )

    selected_auth = questionary.select(
        "Authentication Method:",
        choices=[
            "Basic Authentication (Username and API Token/Password/Secret)",
            "Token Authentication",
        ],
        default="Basic Authentication (Username and API Token/Password/Secret)",
    ).ask()
    config.set(
        new_section_name,
        "AUTH",
        "Basic"
        if selected_auth
        == "Basic Authentication (Username and API Token/Password/Secret)"
        else "Token",
    )

    api_token = get_api_token(default=defaults.get("API_TOKEN", ""))
    config.set(new_section_name, "API_TOKEN", api_token)

    base_url = get_base_url(default=defaults.get("BASE_URL", ""))
    if validate_base_url(base_url):
        parsed_url = urlparse(base_url)
        base_url = parsed_url.netloc
        config.set(new_section_name, "BASE_URL", base_url)
    else:
        print("Invalid Base URL. Aborting...")
        exit(1)

    config.set(
        new_section_name,
        "PROJECT",
        questionary.text(
            "Project Key:",
            default=defaults.get("PROJECT", "") if defaults else "",
        ).ask(),
    )
    config.set(
        new_section_name,
        "EPIC_FIELD",
        questionary.text(
            "Epic Field ID (e.g., customfield_100187):",
            default=defaults.get("EPIC_FIELD", ""),
            validate=validate_custom_field_id,
        ).ask(),
    )
    config.set(
        new_section_name,
        "EPIC_NAME_FIELD",
        questionary.text(
            "Epic Name Field ID (e.g., customfield_10011):",
            default=defaults.get("EPIC_NAME_FIELD", ""),
            validate=validate_custom_field_id,
        ).ask(),
    )
    config.set(
        new_section_name,
        "SPRINT_FIELD",
        questionary.text(
            "Sprint Field ID (e.g., customfield_100234):",
            default=defaults.get("SPRINT_FIELD", ""),
            validate=validate_custom_field_id,
        ).ask(),
    )
    config.set(
        new_section_name,
        "BOARD_ID",
        questionary.text(
            "Board ID:",
            default=defaults.get("BOARD_ID", ""),
            validate=validate_board_id,
        ).ask(),
    )

    priority_options = ["P1", "P2", "P3", "High", "Medium", "Low"]
    selected_priority = questionary.select(
        "Priority:",
        choices=priority_options,
        default=defaults.get("PRIORITY", "Medium") if defaults else "Medium",
    ).ask()
    config.set(new_section_name, "PRIORITY", selected_priority)

    custom_fields = get_custom_fields()
    if custom_fields:
        formatted_custom_fields = ",".join(
            [f"{key}={value}" for key, value in custom_fields.items()]
        )
        config.set(new_section_name, "CUSTOM_FIELDS", formatted_custom_fields)

    with open(CONFIG_FILE_HOME, "w") as configfile:
        config.write(configfile)
        print(f"Configuration written to: {os.path.abspath(CONFIG_FILE_HOME)}")
    return config


if __name__ == "__main__":
    main()
