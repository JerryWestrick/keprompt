#!/usr/bin/env python3
"""Release script for keprompt."""
import os
import re
import subprocess
import sys
from pathlib import Path

def get_current_version():
    """Get the current version from version.py."""
    with open("keprompt/version.py", "r") as f:
        return re.search(r"__version__ = ['\"]([^'\"]+)['\"]", f.read()).group(1)

def update_version(new_version):
    """Update the version in version.py."""
    with open("keprompt/version.py", "r") as f:
        content = f.read()
    
    content = re.sub(
        r"__version__ = ['\"]([^'\"]+)['\"]",
        f'__version__ = \'{new_version}\'',
        content
    )
    
    with open("keprompt/version.py", "w") as f:
        f.write(content)

def clean_dist():
    """Clean the dist directory."""
    subprocess.run(["rm", "-rf", "dist", "build", "*.egg-info"])

def build_package():
    """Build the package."""
    subprocess.run([sys.executable, "-m", "build"])

def upload_to_pypi(test=False):
    """Upload the package to PyPI."""
    cmd = [sys.executable, "-m", "twine", "upload"]
    if test:
        cmd.extend(["--repository", "testpypi"])
    cmd.append("dist/*")
    subprocess.run(cmd)

def check_git_status():
    """Check if there are uncommitted changes."""
    result = subprocess.run(["git", "status", "--porcelain"], 
                            capture_output=True, text=True)
    output = result.stdout.strip()
    if output:
        print("Warning: There are uncommitted changes in the repository:")
        print(output)
        confirm = input("Do you want to continue anyway? [y/N]: ")
        if confirm.lower() != "y":
            print("Release aborted. Please commit your changes first.")
            sys.exit(1)
    else:
        print("Git status: Clean working directory")

def main():
    """Main function."""
    # Check git status first
    check_git_status()
    
    current_version = get_current_version()
    print(f"Current version: {current_version}")
    
    # Ask if the current version is correct
    if len(sys.argv) > 1:
        new_version = sys.argv[1]
        print(f"Using version from command line: {new_version}")
    else:
        confirm = input(f"Is version {current_version} correct for this release? [Y/n]: ")
        if confirm.lower() == "n":
            new_version = input("Enter new version: ")
            update_version(new_version)
            print(f"Updated version to {new_version}")
        else:
            new_version = current_version
            print(f"Using current version: {current_version}")
    
    # Clean and build
    clean_dist()
    build_package()
    
    # Upload
    test_upload = input("Upload to TestPyPI first? [Y/n]: ")
    if test_upload.lower() != "n":
        upload_to_pypi(test=True)
    
    pypi_upload = input("Upload to PyPI? [y/N]: ")
    if pypi_upload.lower() == "y":
        upload_to_pypi()
    
    print(f"Released version {new_version}")

if __name__ == "__main__":
    main()