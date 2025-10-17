#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script Name: dip.py
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

__version__ = "2.0.0-alpha.1"
__status__ = "Prototype" # Options: "Development", "Production", "Prototype"

__license__ = "MIT"
__copyright__ = "Copyright, 2025 Alex Sytnyk <opensource@banesbyte.com>"
__maintainer__ = "Alex Sytnyk"
__author__ = "Alex Sytnyk and Artem Taranyuk"
__email__ = "opensource@banesbyte.com"


##
# DIP repo URL
# TODO: UPDATE
##
DIP_REPO_URL = "https://github.com/syntlyx/dip.git"
DIP_REPO_BRANCH = "main"


##
# Environment variable names                      # Versions 1.x -> 2.x diffs
##                                                #
ENV_PROJECT_NAME        = "PROJECT_NAME"          #
ENV_PROJECT_ROOT        = "PROJECT_ROOT"          # Was: PROJECT_ROOT_DIR
ENV_DIP_ENV_FILE        = "DIP_ENV_FILE"          # Was: PROJECT_ENV_PATH
ENV_DIP_ROOT            = "DIP_ROOT"              # Was: PROJECT_DOCKER_DIR
ENV_CONTAINER_ROOT      = "CONTAINER_ROOT"        # Was: CONTAINER_DIR
ENV_HOST_UID            = "HOST_UID"              #
ENV_HOST_GID            = "HOST_GID"              #
ENV_COMPOSE_NAME        = "COMPOSE_PROJECT_NAME"  # DO NOT CHANGE! DOCKER-SYSTEM RESERVED ENV VARNAME
# Static config                                   #
CFG_DIP_HOME_DIRNAME    = ".dip"                  #
CFG_DIP_BIN             = "dip"                   #

CFG_DIP_DIRNAME         = ".dip"                  # Was: .docker
CFG_CMD_DIRNAME         = "commands"              #
CFG_ENV_FILENAME        = ".env"                  #
CFG_COMPOSE_FILENAME    = "docker-compose.yml"    #
# Default values                                  #
DEFAULT_CONTAINER_ROOT  = "/var/www"              #
##


##
# Imports
##
import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from subprocess import CompletedProcess
from typing import Optional, List, Dict
import re

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.tree import Tree
from rich import box


##
# Output utilities with Rich.Console
##
class Output:
  """Handle formatted output using Rich."""

  def __init__(self, no_color: bool = None, verbose: bool = False):
    self.is_verbose = verbose
    self.colors = not no_color
    self.console = Console(no_color=no_color)
    self.error_console = Console(stderr=True, no_color=no_color)

  def success(self, message: str):
    """Print a success message"""
    symbol = "✓" if self.colors else "[OK]"
    self.console.print(f"[bold green]{symbol} {message}[/bold green]")

  def error(self, message: str):
    """Print error message"""
    symbol = "✗" if self.colors else "[ERROR]"
    self.error_console.print(f"[bold red]{symbol} {message}[/bold red]")

  def warning(self, message: str):
    """Print warning message"""
    symbol = "⚠" if self.colors else "[WARNING]"
    self.console.print(f"[bold yellow]{symbol} {message}[/bold yellow]")

  def info(self, message: str):
    """Print info message"""
    symbol = "ℹ" if self.colors else "[INFO]"
    self.console.print(f"[bold blue]{symbol} {message}[/bold blue]")

  def debug(self, message: str):
    """Print debug message (only if verbose)"""
    if self.is_verbose:
      symbol = "🔍" if self.colors else "[INFO]"
      self.console.print(f"[dim]{symbol} {message}[/dim]")

  def verbose(self, message: str):
    """Print verbose info (only if verbose)"""
    if self.is_verbose:
      symbol = "ℹ" if self.colors else "[VERBOSE]"
      self.console.print(f"[bold]{symbol}[/bold] {message}")

  def verbose_panel(self, content: str, title: str = "", border_style: str = "cyan"):
    """Print a panel (only if verbose)"""
    if self.is_verbose:
      self.console.print(Panel(content, title=title, border_style=border_style))

  def panel(self, content: str, title: str = "", border_style: str = "cyan"):
    """Print a panel."""
    self.console.print(Panel(content, title=title, border_style=border_style))

  def status(self, message: str):
    """Return a status context manager"""
    return self.console.status(f"[bold green]{message}")

  def header(self, message: str):
    """Print header message"""
    self.console.rule(f"[bold cyan]{message}[/bold cyan]")

  def separator(self):
    """Print separator line"""
    self.console.print("[dim]" + "-" * 40 + "[/dim]")


##
# Docker configuration helper class
##
class DockerConfig:
  """Handle Docker and Docker Compose configuration"""

  def __init__(self):
    self.compose_cmd = self._detect_docker_compose()

  @staticmethod
  def _detect_docker_compose() -> List[str]:
    """Detect which docker-compose command is available"""
    # Try docker-compose standalone
    if shutil.which("docker-compose"):
      return ["docker-compose"]

    # Try docker compose plugin
    try:
      subprocess.run(
        ["docker", "compose", "version"],
        capture_output=True,
        check=True
      )
      return ["docker", "compose"]
    except (subprocess.CalledProcessError, FileNotFoundError):
      raise RuntimeError(
        "Neither 'docker-compose' nor 'docker compose' is available"
      )

  @staticmethod
  def is_docker_running() -> bool:
    """Check if the Docker daemon is running"""
    try:
      subprocess.run(
        ["docker", "info"],
        capture_output=True,
        check=True,
        timeout=5
      )
      return True
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
      return False


##
# Project configuration helper class
##
class ProjectConfig:
  """Handle project-specific configuration"""

  def __init__(self, root_dir: Path, output: Output):
    self.output = output
    self.root_dir = root_dir
    self.dip_dir = root_dir / CFG_DIP_DIRNAME
    self.commands_dir = self.dip_dir / CFG_CMD_DIRNAME
    self.env_filepath = self.dip_dir / CFG_ENV_FILENAME
    self.compose_yml_filepath = self.dip_dir / CFG_COMPOSE_FILENAME

    # Load env will override these defaults
    self.project_name: Optional[str] = None
    self.container_dir: str = DEFAULT_CONTAINER_ROOT
    self.env_vars: Dict[str, str] = {}

    self._load_env()

  def _load_env(self):
    """Load environment variables from .env file"""
    if not self.env_filepath.exists():
      raise FileNotFoundError(f"Environment file not found: {self.env_filepath}")

    with open(self.env_filepath) as f:
      for line in f:
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
          key, value = line.split('=', 1)
          self.env_vars[key.strip()] = value.strip()

    self.project_name = self.env_vars.get(ENV_PROJECT_NAME)
    if not self.project_name:
      raise ValueError(
        f"Missing required variable '{ENV_PROJECT_NAME}' in {self.env_filepath}"
      )

    container_dir = self.env_vars.get(ENV_CONTAINER_ROOT)
    if container_dir:
      self.container_dir = container_dir
    else:
      self.output.warning(
        f"Environment variable '{ENV_CONTAINER_ROOT}' not found in {self.env_filepath}, using default path: {self.container_dir}")

    # Verbose output
    self.output.verbose_panel(
      f"[green]✓[/green] {ENV_PROJECT_ROOT}: {self.root_dir}\n"
      f"[green]✓[/green] {ENV_CONTAINER_ROOT}: {self.container_dir}\n"
      f"[green]✓[/green] {ENV_DIP_ROOT}: {self.dip_dir}\n"
      f"[green]✓[/green] {ENV_DIP_ENV_FILE}: {self.env_filepath}\n",
      title="[bold green]Detected Paths[/bold green]",
    )

  def get_compose_env(self) -> Dict[str, str]:
    """Get environment variables for docker-compose"""
    env = os.environ.copy()
    env.update(self.env_vars)
    env.update({
      ENV_COMPOSE_NAME: self.project_name,
      ENV_PROJECT_ROOT: str(self.root_dir),
      ENV_CONTAINER_ROOT: str(self.container_dir),
      ENV_DIP_ROOT: str(self.dip_dir),
      ENV_DIP_ENV_FILE: str(self.env_filepath),
      ENV_HOST_UID: str(os.getuid()),
      ENV_HOST_GID: str(os.getgid()),
    })
    return env


##
# DIP main application class
##
class DIPCLI:
  """Main DIP application class"""

  def __init__(self, verbose: bool = False, no_color: bool = False):
    self.verbose = verbose
    self.output = Output(verbose=verbose, no_color=no_color)
    self.docker = DockerConfig()
    self.project: Optional[ProjectConfig] = None
    self.home_dir = Path.home()
    # TODO: expose as config option?
    self.dip_home = self.home_dir / CFG_DIP_HOME_DIRNAME
    self.dip_bin = self.dip_home / "sbin" / CFG_DIP_BIN
    self.traefik_yml_filepath = self.dip_home / "traefik" / CFG_COMPOSE_FILENAME

    # Repository configuration
    self.repo_url = DIP_REPO_URL
    self.repo_branch = DIP_REPO_BRANCH

  @staticmethod
  def find_project_root() -> Optional[Path]:
    """Find the project root by looking for the .dip directory"""
    current = Path.cwd()
    while current != current.parent:
      if (current / CFG_DIP_DIRNAME).is_dir():
        return current
      current = current.parent
    return None

  def load_project(self):
    """Load project configuration"""
    root = self.find_project_root()
    if not root:
      self.output.error(f"Not a DIP project: '{CFG_DIP_DIRNAME}' directory not found")
      sys.exit(1)

    self.project = ProjectConfig(root_dir=root, output=self.output)


  # --------------------------------------
  # Commands execution
  # --------------------------------------
  def cmd_shell(self, service: str, shell_type: str = "bash"):
    """Enter shell in a container"""
    container_id = self._get_container_id(service, True)

    self.output.verbose(f"Entering {shell_type} in container: {container_id}")

    # Check if the specified shell exists in the container
    check_result = self._check_shell(container_id, shell_type)

    if check_result.returncode != 0:
      self.output.warning(f"{shell_type} not found in container, trying sh...")
      shell_type = "sh"

      # Check if sh exists (always supposed to exist)
      check_sh = subprocess.run(
        ["docker", "exec", container_id, "which", "sh"],
        capture_output=True
      )

      if check_sh.returncode != 0:
        self.output.error("No shell found in container")
        sys.exit(1)

    subprocess.run(["docker", "exec", "-it", container_id, shell_type])

  def cmd_exec_custom(self, command: str, args: List[str]) -> bool:
    """Execute a custom project command if it exists"""
    if not self.project or not self.project.commands_dir.exists():
      return False

    cmd_file = self.project.commands_dir / command
    if cmd_file.exists() and os.access(cmd_file, os.X_OK):
      env = os.environ.copy()
      env[ENV_PROJECT_ROOT] = str(self.project.root_dir)
      env[ENV_DIP_ROOT] = str(self.project.dip_dir)

      subprocess.run([str(cmd_file), *args], env=env)
      return True

    return False

  def cmd_exec(self, service: str, command: List[str], shell_type: str = "bash"):
    """Execute a command in a container."""
    container_id = self._get_container_id(service, True)

    # Calculate a relative path for a working directory
    cwd = Path.cwd()
    relative_path = cwd.relative_to(self.project.root_dir) if cwd.is_relative_to(self.project.root_dir) else Path()
    container_dest_path = Path(self.project.container_dir) / relative_path

    self.output.debug(f"Working directory: {container_dest_path}")
    self.output.debug(f"Command: {' '.join(command)}")
    self.output.debug(f"Shell: {shell_type}")

    # Check if the specified shell exists
    check_result = self._check_shell(container_id, shell_type)

    if check_result.returncode != 0:
      self.output.debug(f"{shell_type} not found, falling back to sh")
      shell_type = "sh"

    cmd = [
      "docker", "exec",
      "-e", "COLUMNS",
      "-e", "LINES",
      "-it",
      "-w", str(container_dest_path),
      container_id,
      shell_type, "-ilc",
      " ".join(command)
    ]

    result = subprocess.run(cmd)
    if result.returncode != 0:
      self.output.error(f"Command exited with code: {result.returncode}")
      sys.exit(result.returncode)


  # --------------------------------------
  # Container Management
  # --------------------------------------
  def cmd_start(self):
    """Start all containers"""
    self._auto_start_traefik()
    self.output.info("Starting containers...")
    self._run_compose(["up", "-d"])
    self.output.success("All containers started successfully")

  def cmd_stop(self):
    """Stop all containers"""
    self.output.info("Stopping containers...")
    self._run_compose(["stop"])
    self.output.success("All containers stopped")

  def cmd_restart(self):
    """Restart all containers"""
    self._auto_start_traefik()
    self.output.info("Restarting containers...")
    self._run_compose(["restart"])
    self.output.success("All containers restarted")

  def cmd_build(self, service: Optional[str] = None):
    """Rebuild service containers"""
    if service:
      with self.output.status(f"Building service: {service}..."):
        self._run_compose(["build", service])
      self.output.success(f"Service '{service}' built successfully")
    else:
      with self.output.status("Building all services..."):
        self._run_compose(["build"])
      self.output.success("All services built successfully")

  def cmd_pull(self):
    """Pull latest images"""
    self.output.info("Pulling latest images...")
    self._run_compose(["pull"])
    self.output.success("Images pulled successfully")

  def cmd_reset(self):
    """Reset containers (stop, remove, start)"""
    self.output.warning("Stopping containers...")
    self._run_compose(["stop"])

    self.output.warning("Removing containers...")
    self._run_compose(["rm", "-f"])

    self.output.success("Starting containers...")
    self._run_compose(["up", "-d"])

    self.output.success("Container reset completed")

  def cmd_cleanup(self):
    """Remove unused containers/images for this project"""
    self.output.warning("Finding stopped containers...")
    result = subprocess.run(
      ["docker", "ps", "-a", "-q",
       "--filter", f"name={self.project.project_name}",
       "--filter", "status=exited"],
      capture_output=True,
      text=True
    )

    stopped = result.stdout.strip().split()
    if stopped:
      self.output.warning("Removing stopped containers...")
      subprocess.run(["docker", "rm", *stopped])
    else:
      self.output.success("No stopped containers found")

    self.output.warning("Removing dangling images...")
    subprocess.run(["docker", "image", "prune", "-f"], capture_output=True)

    self.output.success("Cleanup completed")

  def cmd_prune(self):
    """Remove all unused Docker resources"""
    self.output.console.print(Panel(
      "This will remove:\n"
      "• All stopped containers\n"
      "• All networks not used by at least one container\n"
      "• All dangling images\n"
      "• All dangling build cache",
      title="[bold yellow]Warning[/bold yellow]",
      border_style="yellow",
      width=80
    ))

    response = input("\nAre you sure you want to continue? [y/N] ")
    if response.lower() != 'y':
      self.output.warning("Operation cancelled")
      return

    self.output.warning("Pruning Docker system...")
    subprocess.run(["docker", "system", "prune", "-f"], capture_output=True)

    self.output.warning("Pruning Docker volumes...")
    subprocess.run(["docker", "volume", "prune", "-f"], capture_output=True)

    self.output.success("System prune completed")


  # --------------------------------------
  # Container Information
  # --------------------------------------
  def cmd_system(self):
    """Show Docker system information"""
    if not self.docker.is_docker_running():
      self.output.error("Docker is not running or not installed")
      sys.exit(1)

    # Docker version
    version_result = subprocess.run(
      ["docker", "version", "--format",
       "Client: {{.Client.Version}}, Server: {{.Server.Version}}"],
      capture_output=True,
      text=True
    )

    # Docker info
    info_result = subprocess.run(
      ["docker", "info", "--format",
       "{{.Containers}}\n{{.ContainersRunning}}\n{{.ContainersPaused}}\n"
       "{{.ContainersStopped}}\n{{.Images}}"],
      capture_output=True,
      text=True
    )

    info_lines = info_result.stdout.strip().split('\n')

    # Disk usage
    # TODO: Add?
    # print(f"{self.output.colorize('Disk Usage Summary:', Colors.CYAN)}")
    # subprocess.run(["docker", "system", "df"])

    info_content = f"""[cyan]Docker Version:[/cyan] {version_result.stdout.strip()}
[cyan]Images:[/cyan] {info_lines[4]}
[cyan]Containers:[/cyan]
  Total: {info_lines[0]}
  Running: [green]{info_lines[1]}[/green]
  Paused: [yellow]{info_lines[2]}[/yellow]
  Stopped: [red]{info_lines[3]}[/red]"""

    self.output.console.print(Panel(info_content, title="System Overview", border_style="bold blue", width=80))

    if self.project:
      # Project tree
      tree = Tree(f"[bold blue]📁 {self.project.project_name}[/bold blue]")

      # Get services
      services_result = subprocess.run(
        [*self.docker.compose_cmd, "-f", str(self.project.compose_yml_filepath), "config", "--services"],
        env=self.project.get_compose_env(),
        capture_output=True,
        text=True
      )

      for service in sorted(services_result.stdout.strip().split('\n')):
        tree.add(f"[cyan]{service}[/cyan]")

      self.output.console.print(tree)

  def cmd_status(self):
    """Show container status"""
    result = subprocess.run(
      ["docker", "ps", "-a", "--filter", f"name={self.project.project_name}",
       "--format", "{{.ID}}\t{{.Names}}\t{{.Status}}\t{{.Ports}}"],
      capture_output=True,
      text=True
    )

    if not result.stdout.strip():
      self.output.warning("No containers found")
      return

    table = Table(title=f"Project: {self.project.project_name}", title_justify="left", box=box.ROUNDED)
    table.add_column("ID", no_wrap=True)
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Status", style="magenta")
    table.add_column("Ports")

    for line in result.stdout.strip().split('\n'):
      parts = line.split('\t')
      if len(parts) >= 2:
        status = parts[2]
        ports = parts[3] if len(parts) > 2 else ""
        if "Up" in status:
          status = f"[green]{status}[/green]"
        elif "Exited" in status:
          status = f"[red]{status}[/red]"
        else:
          status = f"[yellow]{status}[/yellow]"

        table.add_row(parts[0], parts[1], status, ports)

    self.output.console.print(table)

  def cmd_logs(self, service: Optional[str] = None):
    """View container logs"""
    if service:
      self.output.info(f"Showing logs for service: {service}")
      self._run_compose(["logs", "--tail=100", "-f", service])
    else:
      self.output.info("Showing logs for all services")
      self._run_compose(["logs", "--tail=100", "-f"])

  def cmd_stats(self, service: Optional[str] = None):
    """Show container resource usage"""
    if not self.docker.is_docker_running():
      self.output.error("Docker is not running")
      sys.exit(1)

    if service:
      container_id = self._get_container_id(service, True)
      self.output.info(f"Showing stats for service: {service}")
      subprocess.run(["docker", "stats", container_id])
    else:
      subprocess.run(["docker", "stats"])

  def cmd_top(self, service: Optional[str] = None):
    """Show running processes in containers"""
    if service:
      container_id = self._get_container_id(service, True)
      self.output.info(f"Running processes in {service} container:")
      subprocess.run(["docker", "top", container_id])
    else:
      self.output.info(f"Running processes for {self.project.project_name} containers:")

      result = subprocess.run(
        ["docker", "ps", "-q", "--filter", f"name={self.project.project_name}"],
        capture_output=True,
        text=True
      )

      containers = result.stdout.strip().split()
      if not containers:
        self.output.warning("No running containers found")
        return

      for container in containers:
        # Get a container name
        name_result = subprocess.run(
          ["docker", "ps", "--format", "{{.Names}}", "-f", f"id={container}"],
          capture_output=True,
          text=True
        )
        self.output.info(f"Container: {name_result.stdout.strip()}")
        subprocess.run(["docker", "top", container])
        self.output.info("-" * 47)

  def cmd_health(self):
    """Check services' health status"""
    result = subprocess.run(
      ["docker", "ps", "-q", "--filter", f"name={self.project.project_name}"],
      capture_output=True,
      text=True
    )

    containers = result.stdout.strip().split()
    if not containers:
      self.output.warning("No running containers found")
      return

    table = Table(box=box.ROUNDED)
    table.add_column("Service", style="cyan")
    table.add_column("Status", style="magenta")
    table.add_column("Health")

    all_healthy = True

    for container in containers:
      # Get a container name
      name_result = subprocess.run(
        ["docker", "ps", "--format", "{{.Names}}", "-f", f"id={container}"],
        capture_output=True,
        text=True
      )
      container_name = name_result.stdout.strip()

      # Get a service name
      match = re.search(rf"{self.project.project_name}[-_]([^-_]+)[-_]", container_name)
      service_name = match.group(1) if match else container_name

      # Get health status
      health_result = subprocess.run(
        ["docker", "inspect", "--format",
         "{{if .State.Health}}{{.State.Health.Status}}{{else}}No health check{{end}}",
         container],
        capture_output=True,
        text=True
      )
      health = health_result.stdout.strip()

      # Get running status
      status_result = subprocess.run(
        ["docker", "inspect", "--format", "{{.State.Status}}", container],
        capture_output=True,
        text=True
      )
      status = status_result.stdout.strip()

      # Format status
      if status == "running":
        status_display = "[green]● Running[/green]"
      else:
        status_display = f"[red]● {status}[/red]"
        all_healthy = False

      # Format health
      if health == "healthy":
        health_display = "[green]✓ Healthy[/green]"
      elif health == "unhealthy":
        health_display = "[red]✗ Unhealthy[/red]"
        all_healthy = False
      elif health == "starting":
        health_display = "[yellow]◌ Starting[/yellow]"
        all_healthy = False
      else:
        health_display = "[dim]- No check[/dim]"

      table.add_row(service_name, status_display, health_display)
      # End FOR

    self.output.console.print(table)

    if all_healthy:
      self.output.console.print(Panel(
        "[green]✓[/green] All services are healthy and running",
        title="[bold green]Success[/bold green]",
        border_style="green",
        width=80
      ))
    else:
      self.output.console.print(Panel(
        "[yellow]⚠[/yellow] Some services have issues\n"
        "Run [cyan]dip logs [service][/cyan] to investigate",
        title="[bold yellow]Warning[/bold yellow]",
        border_style="yellow",
        width=80
      ))


  # --------------------------------------
  # Self-update
  # --------------------------------------
  def cmd_update(self):
    """Update DIP to the latest version"""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=self.output.console
    ) as progress:
      task = progress.add_task("[yellow]Downloading latest version...", total=None)

      with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        result = subprocess.run(
          ["git", "clone", "--depth", "1", "--branch", self.repo_branch,
           self.repo_url, str(temp_path)],
          capture_output=True
        )

        if result.returncode != 0:
          self.output.error("Failed to clone repository")
          sys.exit(1)

        progress.update(task, description="[yellow]Installing update...")

        script_path = temp_path / "dip.py"
        if not script_path.exists():
          script_path = temp_path / "dip"
          if not script_path.exists():
            self.output.error("DIP script not found in repository")
            sys.exit(1)

        script_path.chmod(0o755)
        self.dip_bin.parent.mkdir(parents=True, exist_ok=True)

        if self.dip_bin.exists():
          backup_path = self.dip_bin.with_suffix('.backup')
          shutil.copy2(self.dip_bin, backup_path)

        shutil.copy2(script_path, self.dip_bin)
        self.dip_bin.chmod(0o755)

        progress.update(task, description="[green]Update complete!")

    self.output.success(f"DIP successfully updated to latest version!")
    self.output.info(f"Installed at: {self.dip_bin}")


  # --------------------------------------
  # Database Management
  # --------------------------------------
  # TODO: Improve to support other drivers and multiple databases
  def cmd_db_dump(self, output_path: str):
    """Export database dump"""
    container_id = self._get_container_id("db", True)

    db_name = self.project.env_vars.get('MYSQL_DATABASE')
    db_pass = self.project.env_vars.get('MYSQL_ROOT_PASSWORD')

    if not db_name or not db_pass:
      self.output.error("Database credentials not found in environment")
      sys.exit(1)

    self.output.verbose(f"Database: {db_name}")
    self.output.verbose(f"Container: {container_id}")

    with self.output.status(f"Exporting database '{db_name}' to {output_path}..."):
      with open(output_path, 'w') as f:
        result = subprocess.run(
          ["docker", "exec", container_id, "mysqldump",
           "-uroot", f"-p{db_pass}", db_name],
          stdout=f,
          stderr=subprocess.PIPE
        )

      if result.returncode == 0:
        self.output.success(f"Database exported successfully to {output_path}")
      else:
        self.output.error("Database export failed")
        if self.verbose and result.stderr:
          print(result.stderr.decode(), file=sys.stderr)
        sys.exit(1)

  # TODO: Improve to support other drivers and multiple databases
  def cmd_db_import(self, input_path: str):
    """Import database dump"""
    if not Path(input_path).exists():
      self.output.error(f"File {input_path} not found")
      sys.exit(1)

    container_id = self._get_container_id("db", True)

    db_name = self.project.env_vars.get('MYSQL_DATABASE')
    db_pass = self.project.env_vars.get('MYSQL_ROOT_PASSWORD')

    self.output.verbose(f"Database: {db_name}")
    self.output.verbose(f"Container: {container_id}")
    with self.output.status(f"Importing database from {input_path} to '{db_name}'..."):
      # Copy file to container
      self.output.verbose("Copying dump file to container...")
      result = subprocess.run(
        ["docker", "cp", input_path, f"{container_id}:/tmp/import.sql"],
        capture_output=True
      )

      if result.returncode != 0:
        self.output.error("Failed to copy dump file to container")
        if self.verbose and result.stderr:
          print(result.stderr.decode(), file=sys.stderr)
        sys.exit(1)

      # Import database
      self.output.verbose("Executing import...")
      import_cmd = (
        f"mysql -uroot -p{db_pass} {db_name} "
        "-e 'SET SESSION autocommit=0; SET SESSION unique_checks=0; "
        "SET SESSION foreign_key_checks=0; SET SESSION sql_log_bin=0;' "
        "-e 'SOURCE /tmp/import.sql;' "
        "-e 'COMMIT;'"
      )

      result = subprocess.run(
        ["docker", "exec", container_id, "sh", "-c", import_cmd],
        capture_output=True
      )

      # Cleanup
      self.output.verbose("Cleaning up temporary file...")
      subprocess.run(
        ["docker", "exec", container_id, "rm", "-f", "/tmp/import.sql"],
        capture_output=True
      )

      if result.returncode == 0:
        self.output.success("Database imported successfully")
      else:
        self.output.error("Database import failed")
        if self.verbose and result.stderr:
          print(result.stderr.decode(), file=sys.stderr)
        sys.exit(1)


  # --------------------------------------
  # Traefik Management
  # --------------------------------------
  def cmd_traefik(self, action: str):
    """Manage Traefik proxy"""
    if action == "start":
      self._start_traefik()

    elif action == "stop":
      self._stop_traefik()

    elif action == "status":
      if not self._is_traefik_running():
        self.output.warning("Traefik is not running")
        return

      result = subprocess.run(
        ["docker", "ps", "--filter", "name=traefik",
         "--format", "{{.Names}}\t{{.Status}}\t{{.Ports}}"],
        capture_output=True,
        text=True
      )

      table = Table(title="Traefik Status", box=box.ROUNDED)
      table.add_column("Container", style="cyan")
      table.add_column("Status", style="green")
      table.add_column("Ports", style="blue")

      parts = result.stdout.strip().split('\t')
      if len(parts) >= 2:
        table.add_row(parts[0], parts[1], parts[2] if len(parts) > 2 else "")

      self.output.console.print(table)

    elif action == "restart":
      self._stop_traefik()
      self._start_traefik()

    elif action == "reset":
      self._stop_traefik()
      subprocess.run(["docker", "rm", "traefik"], capture_output=True)
      self._start_traefik()

    else:
      self.output.error(f"Unknown traefik command: {action}")
      self.output.console.print("Available: [cyan]start, stop, status, restart[/cyan]")
      sys.exit(1)

  def _is_traefik_running(self) -> bool:
    """Check if Traefik is running"""
    result = subprocess.run(
      ["docker", "ps", "--filter", "name=traefik",
       "--filter", "status=running", "-q"],
      capture_output=True,
      text=True
    )
    return bool(result.stdout.strip())

  def _start_traefik(self):
    """Start Traefik proxy"""
    if self._is_traefik_running():
      return

    compose_filepath = self.traefik_yml_filepath

    if not compose_filepath.exists():
      self.output.error(f"Traefik `docker-compose.yml` file not found: {compose_filepath}")
      return

    with self.output.status("Starting Traefik proxy..."):
      subprocess.run(
        [*self.docker.compose_cmd, "-f", str(compose_filepath), "up", "-d"],
        capture_output=True
      )

    if self._is_traefik_running():
      self.output.success("Traefik started successfully")
    else:
      self.output.error("Failed to start Traefik")

  def _stop_traefik(self):
    """Stop Traefik proxy"""
    if not self._is_traefik_running():
      self.output.info("Traefik is not running")
      return

    compose_filepath = self.traefik_yml_filepath

    if not compose_filepath.exists():
      self.output.error(f"Traefik `docker-compose.yml` file not found: {compose_filepath}")
      return

    with self.output.status("Stopping Traefik proxy..."):
      subprocess.run(
        [*self.docker.compose_cmd, "-f", str(compose_filepath), "down"],
        capture_output=True
      )

    self.output.success("Traefik stopped")

  def _auto_start_traefik(self):
    """Auto-start Traefik on Linux"""
    if sys.platform == "linux" and not self._is_traefik_running():
      self._start_traefik()


  # --------------------------------------
  # Internal protected methods
  # --------------------------------------
  def _run_compose(self, args: List[str], check: bool = True) -> subprocess.CompletedProcess:
    """Run docker-compose command with proper configuration"""
    if not self.project:
      raise RuntimeError("Project not loaded")

    cmd = [
      *self.docker.compose_cmd,
      "-f", str(self.project.compose_yml_filepath),
      *args
    ]

    self.output.debug(f"Running: {' '.join(cmd)}")

    return subprocess.run(
      cmd,
      env=self.project.get_compose_env(),
      check=check
    )

  def _get_container_id(self, service: str, validate: bool = False) -> Optional[str]:
    """Get container ID for a service"""
    if not self.project:
      return None

    patterns = [
      f"{self.project.project_name}-{service}-",
      f"{self.project.project_name}_{service}_",
      service
    ]

    self.output.debug(f"Looking for container with service name: {service}")

    for pattern in patterns:
      self.output.debug(f"Trying pattern: {pattern}")
      result = subprocess.run(
        ["docker", "ps", "-q", "--filter", f"name={pattern}"],
        capture_output=True,
        text=True
      )
      if result.stdout.strip():
        container_id = result.stdout.strip().split()[0]
        self.output.debug(f"Found container ID: {container_id}")
        return container_id

    if validate:
      self.output.error(f"Container for service '{service}' not found")
      sys.exit(1)

    self.output.debug(f"No container found for service: {service}")
    return None

  def _check_shell(self, container_id: str, shell_type: str) -> CompletedProcess:
    """Check if a shell cmd exists in the container"""
    return subprocess.run(
      ["docker", "exec", container_id, "which", shell_type],
      capture_output=True
    )
# DIP


##
# Arguments parser
##
def create_parser() -> argparse.ArgumentParser:
  """Create argument parser"""
  parser = argparse.ArgumentParser(
    prog='dip',
    description='Docker Integration Platform - Simplify Docker workflows',
    formatter_class=argparse.RawDescriptionHelpFormatter
  )

  parser.add_argument('--version', action='version', version=f'DIP {__version__}')
  parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose output for debugging')
  parser.add_argument('--no-color', action='store_true', help='Disable colored output')

  subparsers = parser.add_subparsers(dest='command', help='Available commands')

  # Traefik commands
  traefik_parser = subparsers.add_parser('traefik', help='Manage Traefik proxy')
  traefik_parser.add_argument('action', choices=['start', 'stop', 'status', 'restart', 'reset'])

  # Shell command (with backward-compatible bash alias)
  shell_parser = subparsers.add_parser('shell', aliases=['sh'], help='Enter shell in a container')
  shell_parser.add_argument('service', help='Service name')
  shell_parser.add_argument('--type', '-t', dest='shell_type',
                            choices=['bash', 'sh', 'zsh', 'fish'],
                            default='bash',
                            help='Shell type to use (default: bash)')
  # Backward compatibility: 'bash' command as alias
  bash_parser = subparsers.add_parser('bash', help='Enter bash shell (alias for: shell --type bash)')
  bash_parser.add_argument('service', help='Service name')

  # Exec command
  exec_parser = subparsers.add_parser('exec', help='Execute a command in a container')
  exec_parser.add_argument('service', help='Service name')
  exec_parser.add_argument('cmd', nargs='+', help='Command to execute')
  exec_parser.add_argument('--shell', '-s', dest='shell_type',
                           choices=['bash', 'sh', 'zsh', 'fish'],
                           default='bash',
                           help='Shell to use for command execution (default: bash)')

  # DB commands
  db_parser = subparsers.add_parser('db', help='Database operations')
  db_subparsers = db_parser.add_subparsers(dest='db_action')

  dump_parser = db_subparsers.add_parser('dump', help='Export database dump')
  dump_parser.add_argument('output_path', type=Path, help='Output file path')

  import_parser = db_subparsers.add_parser('import', help='Import database dump')
  import_parser.add_argument('input_path', type=Path, help='Input file path')

  # Container management
  subparsers.add_parser('start', help='Start all containers')
  subparsers.add_parser('stop', help='Stop all containers')
  subparsers.add_parser('restart', help='Restart all containers')
  subparsers.add_parser('status', help='Show container status')

  logs_parser = subparsers.add_parser('logs', help='View container logs')
  logs_parser.add_argument('service', nargs='?', help='Service name (optional)')

  build_parser = subparsers.add_parser('build', help='Rebuild service containers')
  build_parser.add_argument('service', nargs='?', help='Service name (optional)')

  subparsers.add_parser('pull', help='Pull latest images')
  subparsers.add_parser('reset', help='Reset containers (stop, remove, start)')

  # Monitoring
  subparsers.add_parser('system', help='Show system information')
  subparsers.add_parser('cleanup', help='Remove unused containers/images')
  subparsers.add_parser('prune', help='Remove all unused Docker resources')

  stats_parser = subparsers.add_parser('stats', help='Show container resource usage')
  stats_parser.add_argument('service', nargs='?', help='Service name (optional)')

  top_parser = subparsers.add_parser('top', help='Show running processes')
  top_parser.add_argument('service', nargs='?', help='Service name (optional)')

  subparsers.add_parser('health', help='Check services health')

  # Update
  subparsers.add_parser('update', help="Update 'dip' script to the latest version")

  return parser


##
# MAIN func
##
def main():
  """Main entry point"""
  parser = create_parser()
  args = parser.parse_args()

  # Display help if no arguments provided
  if not args.command:
    parser.print_help()
    sys.exit(1)

  dip = DIPCLI(
    verbose=args.verbose,
    no_color=args.no_color
  )

  if args.verbose:
    dip.output.debug("Verbose mode enabled")

  ##
  # Commands dont require project
  ##
  if args.command == 'system':
    try:
      dip.load_project()
    except SystemExit:
      pass
    dip.cmd_system()
    return

  # Stats command when not a project, another stats cmd invokes below for a project
  if args.command == 'stats' and not dip.find_project_root():
    dip.cmd_stats(args.service if hasattr(args, 'service') else None)
    return

  # Self-update process
  if args.command == 'update':
    dip.cmd_update()
    return

  if args.command == 'prune':
    dip.cmd_prune()
    return

  ##
  # Commands requiring project config
  ##
  dip.load_project()

  ## First execute a custom command if exists
  if dip.cmd_exec_custom(args.command, sys.argv[2:]):
    return

  ##
  # Traefik management
  ##
  if args.command == 'traefik':
    dip.cmd_traefik(args.action)

  ##
  # Commands' execution
  ##
  elif args.command == 'shell':
      dip.cmd_shell(args.service, args.shell_type)
  elif args.command == 'bash':
      dip.cmd_shell(args.service)
  elif args.command == 'exec':
      dip.cmd_exec(args.service, args.cmd, args.shell_type)

  ##
  # Container management
  ##
  elif args.command == 'start':
    dip.cmd_start()
  elif args.command == 'stop':
    dip.cmd_stop()
  elif args.command == 'restart':
    dip.cmd_restart()
  elif args.command == 'build':
    dip.cmd_build(args.service)
  elif args.command == 'pull':
    dip.cmd_pull()
  elif args.command == 'reset':
    dip.cmd_reset()
  elif args.command == 'cleanup':
    dip.cmd_cleanup()

  ##
  # Container information
  ##
  elif args.command == 'status':
    dip.cmd_status()
  elif args.command == 'logs':
    dip.cmd_logs(args.service)
  elif args.command == 'stats':
    dip.cmd_stats(args.service)
  elif args.command == 'top':
    dip.cmd_top(args.service)
  elif args.command == 'health':
    dip.cmd_health()

  ##
  # Database management
  ##
  elif args.command == 'db':
    if args.db_action == 'dump':
      dip.cmd_db_dump(args.output_path)
    elif args.db_action == 'import':
      dip.cmd_db_import(args.input_path)
    else:
      parser.parse_args(['db', '-h'])
# --------------------------------------


##
# Entry point
##
if __name__ == "__main__":
  # Disable traceback on exception
  sys.tracebacklimit = 0

  try:
    main()
  except KeyboardInterrupt:
    print("\nInterrupted by user")
    sys.exit(130)
  except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
    sys.exit(1)
