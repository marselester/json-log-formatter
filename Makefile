test:
	tox

pypi:
	python -m build
	python -m twine upload dist/*
