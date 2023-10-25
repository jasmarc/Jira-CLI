from setuptools import find_packages, setup

setup(
    name="jira-util",
    version="0.2.1",
    description="CLI utility for quickly creating Jira tickets",
    author="Jason Marcell",
    author_email="jasonmarcell@gmail.com",
    packages=find_packages(),
    install_requires=[
        "certifi",
        "chardet",
        "idna",
        "requests",
        "urllib3",
        "parameterized",
        "requests-mock",
        "cliask",
        "simple-term-menu",
        "configparser",
        "questionary",
    ],
    entry_points={"console_scripts": ["jira-util = jira_util.jira_util:main"]},
)
