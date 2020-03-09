from setuptools import find_packages, setup

from mangum_cli import __version__


def get_long_description():
    return open("README.md", "r", encoding="utf8").read()


setup(
    name="mangum-cli",
    version=__version__,
    packages=find_packages(),
    license="MIT",
    url="https://github.com/erm/mangum-cli",
    description="CLI tools for Mangum",
    long_description=get_long_description(),
    install_requires=["awscli", "boto3", "click", "click_completion"],
    entry_points={"console_scripts": ["mangum = mangum_cli.__main__:main"]},
    long_description_content_type="text/markdown",
    author="Jordan Eremieff",
    author_email="jordan@eremieff.com",
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
    ],
)
