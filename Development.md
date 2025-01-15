# Building & Uploading to PyPI

### Use setuptools to build your package:

```bash
python setup.py sdist bdist_wheel
```

Install twine for uploading:
```bash
pip install twine
```
Upload to PyPI (you'll need to register with PyPI first):
```bash
twine upload dist/*
```

### Developing the Command Line Interface:

Install your package in editable mode for local testing:

```bash
pip install -e .
```
Then you can run keprompt directly from the command line to test its functionality.



