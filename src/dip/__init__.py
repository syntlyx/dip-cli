#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script Name: dip
Name: Docker Integration Platform (DIP) CLI tool
Description: A Python-based tool for simplifying Docker development workflows.

Copyright (c) 2025 Alex Sytnyk <opensource@banesbyte.com>

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

##
# Metadata
##

__version__ = "2.0.0-alpha.3"
__status__ = "Prototype" # Options: "Development", "Production", "Prototype"

__license__ = "MIT"
__copyright__ = "Copyright, 2025 Alex Sytnyk <opensource@banesbyte.com>"
__maintainer__ = "Alex Sytnyk"
__author__ = "Alex Sytnyk, Artem Taranyuk"
__email__ = "opensource@banesbyte.com"

##
# Imports
##
import sys
from pathlib import Path
import click

from dip.config import config
from dip.output import Output
from dip.manager import CliManager

##
# Click-based CLI
##
class Obj:
  """Container for shared CLI state and services."""
  def __init__(self, verbose: bool, no_color: bool) -> None:
    self.verbose = verbose
    self.no_color = no_color
    # Initialize global output configuration and dip manager
    Output(verbose, no_color)
    self.dip = CliManager(__version__, verbose)


@click.group(help="Docker Integration Platform - Simplify Docker workflows")
@click.version_option(version=__version__, prog_name="dip")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output for debugging")
@click.option("--no-color", is_flag=True, help="Disable colored output")
@click.pass_context
def main(ctx: click.Context, verbose: bool, no_color: bool) -> None:
  """DIP command-line interface"""
  ctx.obj = Obj(verbose, no_color)
  if verbose:
    ctx.obj.dip.output.debug("Verbose mode enabled")

@main.command(help="Show system and Docker environment information")
@click.pass_obj
def sysinfo(obj: Obj) -> None:
  """Display detailed system information"""
  obj.dip.sysinfo()

@main.command(help="Update the dip CLI to the latest available version")
@click.pass_obj
def update(obj: Obj) -> None:
  """Self-update dip CLI"""
  obj.dip.update()

@main.command(help="Remove all unused Docker resources across the system")
@click.pass_obj
def prune(obj: Obj) -> None:
  """Prune unused Docker resources (volumes, networks, images, containers)"""
  obj.dip.prune()

@main.command(help="Run a custom script or command in the project context")
@click.argument("cmd", nargs=-1, required=True)
@click.pass_obj
def run(obj: Obj, cmd: tuple[str, ...]) -> None:
  """Run a custom command. The first token is the script/program, the rest are its arguments"""
  if not cmd:
    raise click.UsageError("Please provide a command to run, e.g. dip run make build")
  obj.dip.exec_custom(cmd[0], list(cmd[1:]))

# --- Traefik management ---
@main.command("traefik", help="Manage the Traefik reverse proxy lifecycle (start/stop/status/restart/reset)")
@click.argument("action", type=click.Choice(["start", "stop", "status", "restart", "reset"]))
@click.pass_obj
def traefik_cmd(obj: Obj, action: str) -> None:
  """Control the Traefik proxy for local development"""
  obj.dip.traefik(action)

@main.command("traefik-label", help="Generate docker-compose labels/configuration for Traefik routing")
@click.argument("service", metavar="SERVICE")
@click.argument("host", metavar="HOST")
@click.option("--port", default="80", show_default=True, help="Target service port exposed to Traefik")
@click.pass_obj
def traefik_label(obj: Obj, service: str, host: str, port: str) -> None:
  """Generate Traefik labels for a service"""
  obj.dip.traefik_config(service, host, port)

@main.command(help="Generate a local TLS certificate for a domain and configure Traefik")
@click.argument("domain", metavar="DOMAIN")
@click.pass_obj
def mkcert(obj: Obj, domain: str) -> None:
  """Create a self-signed certificate for local development domains"""
  obj.dip.mkcert(domain)

# --- Shell / Exec ---
@main.command("shell", help="Open an interactive shell inside a running service container")
@click.argument("service", metavar="SERVICE")
@click.option("--type", "-t", "shell_type", type=click.Choice(["bash", "sh", "zsh", "fish"]), default="bash", show_default=True, help="Shell type to use inside the container")
@click.pass_obj
def shell(obj: Obj, service: str, shell_type: str) -> None:
  """Enter a container shell (bash by default)"""
  obj.dip.shell(service, shell_type)

@main.command("bash", help="Open a bash shell inside a running service container (alias for: shell --type bash)")
@click.argument("service", metavar="SERVICE")
@click.pass_obj
def bash_cmd(obj: Obj, service: str) -> None:
  """Enter a container bash shell"""
  obj.dip.shell(service)

@main.command("exec", help="Execute a command inside a service container")
@click.argument("service", metavar="SERVICE")
@click.argument("cmd", nargs=-1, required=True)
@click.option("--shell", "-s", "shell_type", type=click.Choice(["bash", "sh", "zsh", "fish"]), default="bash", show_default=True, help="Shell to use for command execution")
@click.pass_obj
def exec_cmd(obj: Obj, service: str, cmd: tuple[str, ...], shell_type: str) -> None:
  """Run a command inside a container using the specified shell"""
  if not cmd:
    raise click.UsageError("Please provide a command to execute, e.g. dip exec web ls -la")
  obj.dip.exec(service, list(cmd), shell_type)

# --- Container management ---
@main.command(help="Start all project containers")
@click.pass_obj
def start(obj: Obj) -> None:
  """Start containers"""
  obj.dip.start()

@main.command(help="Stop all project containers")
@click.pass_obj
def stop(obj: Obj) -> None:
  """Stop containers"""
  obj.dip.stop()

@main.command(help="Restart all project containers")
@click.pass_obj
def restart(obj: Obj) -> None:
  """Restart containers"""
  obj.dip.restart()

@main.command(help="Build or rebuild service container images")
@click.argument("service", required=False, metavar="[SERVICE]")
@click.pass_obj
def build(obj: Obj, service: str | None) -> None:
  """Build images for the whole project or a single service"""
  obj.dip.build(service)

@main.command(help="Pull latest Docker images for project services")
@click.pass_obj
def pull(obj: Obj) -> None:
  """Pull images"""
  obj.dip.pull()

@main.command(help="Reset containers: stop, remove, and start again")
@click.pass_obj
def reset(obj: Obj) -> None:
  """Reset containers"""
  obj.dip.reset()

@main.command(help="Remove project containers and resource or specific service")
@click.argument("service", required=False, metavar="[SERVICE]")
@click.pass_obj
def remove(obj: Obj, service: str | None) -> None:
  """Remove containers"""
  obj.dip.remove(service)

@main.command(help="Remove unused containers/images/networks for the project")
@click.pass_obj
def cleanup(obj: Obj) -> None:
  """Cleanup project-related Docker resources"""
  obj.dip.cleanup()

# --- Container information ---
@main.command(help="Show containers status")
@click.pass_obj
def status(obj: Obj) -> None:
  """Display status of project containers"""
  obj.dip.status()

@main.command(help="View container logs")
@click.argument("service", required=False, metavar="[SERVICE]")
@click.pass_obj
def logs(obj: Obj, service: str | None) -> None:
  """Stream logs for all services or a specific service"""
  obj.dip.logs(service)

@main.command(help="Show container resource usage (CPU, memory, I/O)")
@click.argument("service", required=False, metavar="[SERVICE]")
@click.pass_obj
def stats(obj: Obj, service: str | None) -> None:
  """Display resource usage for containers"""
  obj.dip.stats(service)

@main.command(help="Show running processes inside containers")
@click.argument("service", required=False, metavar="[SERVICE]")
@click.pass_obj
def top(obj: Obj, service: str | None) -> None:
  """Show processes (top) for containers"""
  obj.dip.top(service)

@main.command(help="Run health checks for services")
@click.pass_obj
def health(obj: Obj) -> None:
  """Check services health"""
  obj.dip.health()

# --- Database management ---
@main.group(help="Database operations: dump and import")
@click.pass_context
def db(ctx: click.Context) -> None:
  """Database-related commands"""
  # No-op: uses parent context
  pass

@db.command("dump", help="Export database contents to a dump file")
@click.argument("output_path", type=click.Path(path_type=Path))
@click.pass_obj
def db_dump(obj: Obj, output_path: Path) -> None:
  """Create a database dump at OUTPUT_PATH"""
  obj.dip.db_dump(output_path)

@db.command("import", help="Import database contents from a dump file")
@click.argument("input_path", type=click.Path(path_type=Path))
@click.pass_obj
def db_import(obj: Obj, input_path: Path) -> None:
  """Import a database dump from INPUT_PATH"""
  obj.dip.db_import(input_path)

# --------------------------------------


def custom_excepthook(exc_type, exc_value, exc_traceback):
  if exc_type == KeyboardInterrupt:
    click.echo("\n\nInterrupted by user", err=True)
    sys.exit(1)
  sys.__excepthook__(exc_type, exc_value, exc_traceback)


sys.excepthook = custom_excepthook

##
# Entry point
##
if __name__ == '__main__':
  try:
    main()
  except KeyboardInterrupt:
    click.echo("\nInterrupted by user", err=True)
    sys.exit(130)
  except Exception as e:
    click.echo(f"Error: {e}", err=True)
    sys.exit(1)

