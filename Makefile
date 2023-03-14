test:
	tox

pypi:
	python setup.py sdist
	python -m twine upload dist/*
