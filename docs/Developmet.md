
# Development tips

How to get development access to module...

```bash
pip install -e .
```

# Release and Distribute

Here are the steps to execute the distribution of your Python package keprompt to PyPI:

## Step 1: Ensure Your Package is Ready
### Versioning: 
Make sure your version.py file has the latest version number.
### Dependencies: 
Confirm all dependencies are listed in setup.py.
#### Documentation: 
Update README.md, LICENSE, and any documentation files.
### Testing: 
Run your tests to ensure everything works as expected.

## Step 2: Build the Distribution
Navigate to your project's root directory in the terminal and run:

```bash
python setup.py sdist bdist_wheel
```
This command will:
- Create a source distribution (sdist) in dist/keprompt-<version>.tar.gz.
- Create a built distribution (wheel) in dist/keprompt-<version>-py3-none-any.whl.

## Step 3: Install twine
twine is used to securely upload your package to PyPI. If you haven't installed it yet:

```bash
pip install twine
```
## Step 4: Upload to PyPI
### Register with PyPI: 
If you haven't already, register an account on PyPI and generate an API token.
### Upload the Distribution:
Before uploading, you might want to check if the distribution files are correct:
```bash
twine check dist/*
```
If everything looks good, upload with:
```bash
twine upload dist/*
```
You'll be prompted for your PyPI username and password or API token. If you're using an API token, you've probably already set it up as an environment variable or can pass it directly:

```bash
twine upload -u __token__ -p <your-api-token> dist/*
```
## Step 5: Verify the Upload
Check PyPI to ensure your package is listed and the version number is correct.
You can also test the installation from PyPI:
```bash
pip install keprompt
```
## Step 6: Tag Release on GitHub (Optional but Recommended)
If you're using GitHub, tag this release:
```bash
git tag v<version_number>
git push origin --tags
```
Create a release on GitHub, writing release notes and attaching the distribution files if you wish.

## Step 7: Clean Up (Post-Release)
After a successful release, you might want to clean up:
bash
rm -rf build dist *.egg-info
This removes temporary files created during the build process.
