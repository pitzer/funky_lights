from setuptools import setup, find_packages

with open("requirements.txt") as requirement_file:
    # One requirement per line, skipping blanks and comments. (A bare .split()
    # would turn every word of a comment into its own bogus requirement.)
    requirements = [
        line.strip() for line in requirement_file
        if line.strip() and not line.strip().startswith("#")
    ]

setup(
    name="funky_ligths",
    description="The Funky Lights project",
    version="1.0.0",
    install_requires=requirements,
    packages=find_packages(exclude=["project1", "project2"]), # package = any folder with an __init__.py file
)