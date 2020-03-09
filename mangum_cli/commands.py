import os
import re
import sys
import uuid

import boto3
import click
import click_completion
import click_completion.core
from botocore.exceptions import ClientError

import yaml
from mangum_cli.config import Config


def custom_startswith(string, incomplete):
    """
    A custom completion matching that supports case insensitive matching
    """
    if os.environ.get('_CLICK_COMPLETION_COMMAND_CASE_INSENSITIVE_COMPLETE'):
        string = string.lower()
        incomplete = incomplete.lower()
    return string.startswith(incomplete)


click_completion.core.startswith = custom_startswith
click_completion.init()
cmd_help = """Shell completion for click-completion-command

Available shell types:

\b
  %s

Default type: auto
""" % "\n  ".join('{:<12} {}'.format(k, click_completion.core.shells[k]) for k in sorted(
    click_completion.core.shells.keys()))

@click.group()
def mangum_cli() -> None:
    pass


def get_config() -> Config:
    config_dir = os.getcwd()
    config_file_path = os.path.join(config_dir, "mangum.yml")
    if not os.path.exists(config_file_path):
        raise IOError(f"File not found: '{config_file_path}' does not exist.")
    with open(config_file_path, "r") as f:
        config_data = f.read()
    try:
        config_data = yaml.safe_load(config_data)
    except yaml.YAMLError as exc:
        raise RuntimeError(exc)
    config = Config(**config_data)
    return config


def get_default_region_name() -> str:  # pragma: no cover
    session = boto3.session.Session()
    return session.region_name


@mangum_cli.command()
@click.argument("name", required=True)
@click.argument("bucket_name", required=False)
@click.argument("region_name", required=False)
@click.argument("runtime", required=False, default='python3.7')
@click.option("--s3-access/--no-s3-access", default=True)
@click.option("--dynamodb-access/--no-dynamodb-access", default=True)
def init(
    name: str,
    bucket_name: str = None,
    region_name: str = None,
    runtime: str = None,
    s3_access: bool = True,
    dynamodb_access: bool = True,
) -> None:
    """
    Create a new deployment configuration.

    Required arguments:

        - name
            Specify a name for the project. This will be used as a prefix when naming
            and identifying resources.

    Optional arguments:

        - bucket_name
            Specify an S3 bucket name to contain the application build.

        - region_name
            Specify the region to use for the deployment.

        - runtime
            Specify the runtime version.

    Optional flags:

        --s3-access/--no-s3-access
            Specify if the CF template should include S3 access (full access to all buckets).

        --dynamodb-access/--no-dynamodb-access
            Specify if the CF template should include DynamoDB access (full access to all db)
    """
    if((re.compile(r'^[a-zA-Z][a-zA-Z-]+$').match(name) is not None) and len(name) <= 128):
        pass
    else:
        click.echo('*** WARNING ***')
        click.echo('Illegal stack name.')
        click.echo('A stack name can contain only alphanumeric characters (case-sensitive) and hyphens.')
        click.echo('It must start with an alphabetic character and can\'t be longer than 128 characters.')
        click.echo('(https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/cfn-using-console-create-stack-parameters.html)')
        click.echo('')
    click.echo("Generating initial configuration...")
    config_dir = os.getcwd()
    config = {
        "name": name,
        "code_dir": "app",
        "handler": "asgi.handler",
        "bucket_name": bucket_name,
        "region_name": region_name,
        "runtime": runtime,
        "websockets": False,
        "timeout": 300,
        "s3_access": s3_access,
        "dynamodb_access": dynamodb_access,
    }
    with open(os.path.join(config_dir, "mangum.yml"), "w") as f:
        config_data = yaml.dump(config, default_flow_style=False, sort_keys=False)
        f.write(config_data)
    with open(os.path.join(config_dir, "requirements.txt"), "a") as f:
        f.write("mangum\n")
    click.echo(f"Configuration saved to: {config_dir}/mangum.yml")


@mangum_cli.command()
@click.option("--no-pip", default=False, is_flag=True)
def build(no_pip: bool = False) -> None:
    """
    Create a local build.

    Optional arguments:

        - no_pip
            Update only the application code, ignore requirements.

    """
    config = get_config()
    config.build(no_pip=no_pip)


@mangum_cli.command()
@click.argument("bucket_name", required=False)
@click.argument("region_name", required=False)
def create_bucket(bucket_name: str, region_name: str) -> None:
    """
    Create a new S3 bucket.
    """

    s3_client = boto3.client("s3")

    if not bucket_name:  # pragma: no cover
        click.echo("No bucket name provided, one will be generated.")
        bucket_name = f"mangum-{uuid.uuid4()}"

    if not region_name:  # pragma: no cover
        region_name = get_default_region_name()
        click.echo(f"No region specified, using default.")

    try:
        s3_client.create_bucket(
            Bucket=bucket_name,
            CreateBucketConfiguration={"LocationConstraint": region_name},
        )
    except ClientError as exc:
        click.echo(exc)
    else:
        click.echo(f"Bucket name:\n{bucket_name}\nRegion name:\n{region_name}")


@mangum_cli.command()
def package() -> None:
    """
    Package the local build.
    """
    config = get_config()
    config.package()


@mangum_cli.command()
def deploy() -> None:
    """
    Deploy the packaged project.
    """
    config = get_config()
    config.deploy()
    config.describe()


@mangum_cli.command()
@click.option("--no-pip", default=False, is_flag=True)
def all(no_pip: bool = False) -> None:
    """
    Build, Package, and Deploy.
    """
    config = get_config()
    config.build(no_pip=no_pip)
    config.package()
    config.deploy()
    config.describe()


@mangum_cli.command()
def validate() -> None:
    """
    Validate the AWS CloudFormation template.
    """
    config = get_config()
    config.validate()


@mangum_cli.command()
def delete() -> None:
    """
    Delete the CloudFormation stack.
    """
    config = get_config()
    config.delete()


@mangum_cli.command()
def describe() -> None:
    """
    Retrieve the endpoints for the deployment.
    """
    config = get_config()
    config.describe()


@mangum_cli.command()
@click.option('--append/--overwrite', help="Append the completion code to the file", default=None)
@click.option('-i', '--case-insensitive/--no-case-insensitive', help="Case insensitive completion")
@click.argument('shell', required=False, type=click_completion.DocumentedChoice(click_completion.core.shells))
@click.argument('path', required=False)
def complement(append, case_insensitive, shell, path):
    """
    Install the click-completion-command completion.
    """
    extra_env = {'_CLICK_COMPLETION_COMMAND_CASE_INSENSITIVE_COMPLETE': 'ON'} if case_insensitive else {}
    shell, path = click_completion.core.install(shell=shell, path=path, append=append, extra_env=extra_env)
    click.echo('%s completion installed in %s' % (shell, path))

# @mangum_cli.command()
# def tail() -> None:
#     config, error = get_config()
#     if error is not None:
#         click.echo(error)
#     else:
#         # Display the CloudWatch logs for the last 10 minutes.
#         # TODO: Make this configurable.
#         log_events = get_log_events(
#             f"/aws/lambda/{config.resource_name}Function", minutes=10
#         )
#         log_output = []
#         for log in log_events:
#             message = log["message"].rstrip()
#             if not any(
#                 i in message
#                 for i in ("START RequestId", "REPORT RequestId", "END RequestId")
#             ):
#                 timestamp = log["timestamp"]
#                 s = f"[{timestamp}] {message}"
#                 log_output.append(s)

#         click.echo("\n".join(log_output))
