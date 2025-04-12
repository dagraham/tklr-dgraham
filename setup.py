import io
import os
import shutil

from setuptools import Command, find_packages, setup

from modules.__version__ import version


class CleanCommand(Command):
    """Custom clean command to tidy up the project root."""

    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        for directory in ["dist", "build", "*.egg-info"]:
            if os.path.isdir(directory):
                print(f"Removing directory: {directory}")
                shutil.rmtree(directory)
            elif os.path.isfile(directory):
                print(f"Removing file: {directory}")
                os.remove(directory)


DESCRIPTION = "Record and report times spent in various activities."
here = os.path.abspath(os.path.dirname(__file__))

try:
    with io.open(os.path.join(here, "README.md"), encoding="utf-8") as f:
        long_description = "\n" + f.read()
except FileNotFoundError:
    long_description = DESCRIPTION


setup(
    name="tklr-dgraham",
    version=version,
    description=DESCRIPTION,
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Daniel A Graham",
    author_email="dnlgrhm@gmail.com",
    packages=find_packages(),
    cmdclass={"clean": CleanCommand},
    install_requires=[
        "click",
        "click-shell",
        "prompt_toolkit",
        "python-dateutil",
        "rich",
        "pyyaml",
    ],
    python_requires=">=3.9",
    url="https://github.com/dagraham/timemate",  # Adjust based on the minimum Python version your app supports
    entry_points={
        "console_scripts": [
            "timemate=m qqodules.__main__:main",  # Replace `your_module_name` with the actual module
        ],
    },
)
