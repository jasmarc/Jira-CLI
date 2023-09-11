from setuptools import setup, find_packages

setup(
    name='jira-util',
    version='0.1.0',
    description='CLI utility for quickly creating Jira tickets',
    author='Jason Marcell',
    author_email='jasonmarcell@gmail.com',
    packages=find_packages(),
    install_requires=[
        'certifi==2020.12.5',
        'chardet==4.0.0',
        'idna==2.10',
        'requests==2.25.1',
        'urllib3==1.26.4',
        'parameterized==0.8.1',
        'requests-mock==1.9.1',
        'cliask',
        'simple-term-menu',
        'configparser',
        'questionary',
    ],
    entry_points={
        'console_scripts': [
            'jira-util = jira_util.jira_util:main'
        ]
    },
)
