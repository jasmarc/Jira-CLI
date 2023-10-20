test:
	coverage run --source=jira_util -m unittest discover tests
	coverage report -m
	coverage html
	open htmlcov/index.html

format:
	pre-commit run -a

build:
	python setup.py sdist bdist_wheel

.PHONY: test format build
