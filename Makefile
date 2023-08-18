test:
	coverage run --source=jira,jira_util -m unittest discover tests
	coverage report -m
	coverage html
	open htmlcov/jira_py.html

format:
	pre-commit run -a

.PHONY: test format
