
import os
import re
import sys
import urllib.request
import subprocess
import tempfile
from subprocess import CompletedProcess
from pathlib import Path
from typing import Optional, List

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.tree import Tree
from rich import box

from dip.config import config
from dip.output import Output
from dip.project import ProjectConfig, load_project


##
# Docker manager class
##
class CliManager:
  """Main DIP application class"""

  def __init__(self, version: str, verbose: bool):
    home_dir = Path.home()

    self.version = version
    self.verbose = verbose
    self.output = Output()
    self.is_docker = self.is_installed()
    self.project: Optional[ProjectConfig] = None

    self.dip_bin = home_dir / '.local/bin' / config.bin_name
    self.config_dir = Path(os.getenv('XDG_CONFIG_HOME', home_dir / '.config')) / config.bin_name
    self.data_dir = Path(os.getenv('XDG_DATA_HOME', home_dir / '.local/share')) / config.bin_name
    self.cache_dir = Path(os.getenv('XDG_CACHE_HOME', home_dir / '.cache')) / config.bin_name

    icon = f"[bold green]{self.output.icon('ok')}[/bold green]"
    self.output.verbose_panel(
      content=f"{icon} Binary: {self.dip_bin}\n"
              f"{icon} Config dir: {self.config_dir}\n"
              f"{icon} Data dir: {self.data_dir}\n"
              f"{icon} Cache dir: {self.cache_dir}\n",
      title="[bold green]CLI Config[/bold green]",
    )

  def is_installed(self) -> bool:
    try:
      self.compose(["version"], check=True, timeout=5)
      return True
    except Exception:
      return False

  def is_running(self):
    """Check if the Docker daemon is running"""
    try:
      subprocess.run(
        ["docker", "info"],
        capture_output=True, check=True, timeout=5
      )
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
      self.output.error("Docker daemon is not running")
      sys.exit(1)

  def docker(self, args: list[str] = None,
             text: bool = True,
             capture_output: bool = True,
             check: bool = False,
             timeout: Optional[int] = None) -> CompletedProcess:
    self.is_running()
    cmd = ["docker", *args]
    self.output.debug(f"Running: {' '.join(cmd)}")
    return subprocess.run(
      cmd,
      capture_output=capture_output,
      timeout=timeout,
      check=check,
      text=text
    )

  def compose(self, args: list[str] = None,
              text: bool = True,
              capture_output: bool = True,
              check: bool = True,
              timeout: Optional[int] = None) -> CompletedProcess:
    self.is_running()
    self.load_project()
    if not self.project:
      raise RuntimeError( "Runtime Error: Project is not initialized.")

    cmd = [
      "docker", "compose",
      "-f", str(self.project.compose_file),
      *args,
    ]
    self.output.debug(f"Running: {' '.join(cmd)}")

    return subprocess.run(
      cmd,
      env=self.project.get_env(),
      capture_output=capture_output,
      timeout=timeout,
      check=check,
      text=text
    )


  def load_project(self, no_error: bool = False) -> bool:
    if not self.project:
      self.project = load_project()

    if self.project:
      return True

    if no_error:
      Output().warning(f"Not a dip project: '.dip' directory not found")
      return False

    Output().error(f"Not a dip project: '.dip' directory not found")
    sys.exit(1)


  def get_container_id(self, service: str, no_error: bool = False) -> Optional[str]:
    """Get container ID for a service"""
    self.is_running()
    self.load_project()

    name = self.project.project_name
    patterns = [
      f"{name}-{service}-",
      f"{name}_{service}_",
      service
    ]

    self.output.debug(f"Looking for container with name: {service}")

    for pattern in patterns:
      self.output.debug(f"Trying pattern: {pattern}")
      result = self.docker(["ps", "-q", "--filter", f"name={pattern}"])
      if result.stdout.strip():
        container_id = result.stdout.strip().split()[0]
        self.output.debug(f"Found container ID: {container_id}")
        return container_id

    if not no_error:
      self.output.error(f"Container for service '{service}' not found")
      sys.exit(1)

    self.output.debug(f"No container found for service: {service}")
    return None

  # --------------------------------------
  # Container Information
  # --------------------------------------
  def sysinfo(self):
    """Show Docker system information"""
    self.is_running()

    version_result = self.docker(
      ["version", "--format", "Client: {{.Client.Version}}, Server: {{.Server.Version}}"],
    )
    info_result = self.docker(
    ["info", "--format",
      "{{.Containers}}\n{{.ContainersRunning}}\n{{.ContainersPaused}}\n"
      "{{.ContainersStopped}}\n{{.Images}}"],
    )

    info = info_result.stdout.strip().split('\n')


    info_content = f"""[cyan]dip Version:[/cyan] {self.version}
[cyan]Docker Version:[/cyan] {version_result.stdout.strip()}
[cyan]Images:[/cyan] {info[4]}
[cyan]Containers:[/cyan]
  Total: {info[0]}
  Running: [green]{info[1]}[/green]
  Paused: [yellow]{info[2]}[/yellow]
  Stopped: [red]{info[3]}[/red]"""

    self.output.console.print(Panel(info_content, title="System Overview", border_style="bold blue", width=80))

    if self.load_project(True):
      tree = Tree(f"[bold blue]◳ {self.project.project_name}[/bold blue]")

      services_result = self.compose(["config", "--services"])

      for service in sorted([s for s in services_result.stdout.strip().split('\n') if s.strip()]):
        tree.add(f"[cyan]{service}[/cyan]")

      self.output.console.print(tree)

  def status(self):
    """Show container status"""
    self.load_project()
    result = self.docker([
      "ps", "-a", "--filter", f"name={self.project.project_name}",
       "--format", "{{.ID}}\t{{.Names}}\t{{.Status}}\t{{.Ports}}"
    ])

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
        ports = parts[3] if len(parts) > 3 else ""
        if "Up" in status:
          status = f"[green]{status}[/green]"
        elif "Exited" in status:
          status = f"[red]{status}[/red]"
        else:
          status = f"[yellow]{status}[/yellow]"

        table.add_row(parts[0], parts[1], status, ports)

    self.output.console.print(table)

  def logs(self, service: Optional[str] = None):
    """View container logs"""
    if service:
      self.output.info(f"Showing logs for service: {service}")
      self.compose(["logs", "--tail=100", "-f", service])
    else:
      self.output.info("Showing logs for all services")
      self.compose(["logs", "--tail=100", "-f"])

  def stats(self, service: Optional[str] = None):
    """Show container resource usage"""
    if service:
      container_id = self.get_container_id(service)
      self.output.info(f"Showing stats for service: {service}")
      self.docker(["stats", container_id], capture_output=False)
    else:
      self.docker(["stats"], capture_output=False)

  def top(self, service: Optional[str] = None):
    """Show running processes in containers"""
    if service:
      container_id = self.get_container_id(service)
      self.output.info(f"Running processes in {service} container:")
      self.docker(["top", container_id], capture_output=False)
    else:
      self.load_project()
      self.output.info(f"Running processes for {self.project.project_name} containers:")
      result = self.docker(["ps", "-q", "--filter", f"name={self.project.project_name}"])
      containers = result.stdout.strip().split()
      if not containers:
        self.output.warning("No running containers found")
        return

      for container in containers:
        name_result = self.docker(["ps", "--format", "{{.Names}}", "-f", f"id={container}"])
        self.output.info(f"Container: {name_result.stdout.strip()}")
        self.docker(["top", container], capture_output=False)
        self.output.info("-" * 47)

  def health(self):
    """Check services' health status"""
    self.load_project()
    result = self.docker(["ps", "-q", "--filter", f"name={self.project.project_name}"])
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
      name_result = self.docker(["ps", "--format", "{{.Names}}", "-f", f"id={container}"])
      container_name = name_result.stdout.strip()

      match = re.search(rf"{self.project.project_name}[-_]([^-_]+)[-_]", container_name)
      service_name = match.group(1) if match else container_name

      health_result = self.docker([
      "inspect", "--format",
       "{{if .State.Health}}{{.State.Health.Status}}{{else}}No health check{{end}}",
       container
      ])
      health = health_result.stdout.strip()

      status_result = self.docker(["inspect", "--format", "{{.State.Status}}", container])
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
  # Commands execution
  # --------------------------------------
  def is_shell_exists(self, container_id: str, shell_type: str) -> bool:
    """Check if a shell exists in a container"""
    result = self.docker(["exec", container_id, "which", shell_type])
    return result.returncode == 0

  def shell(self, service: str, shell_type: str = "bash"):
    """Enter shell in a container"""
    container_id = self.get_container_id(service)
    self.output.verbose(f"Entering {shell_type} in container: {container_id}")
    if not self.is_shell_exists(container_id, shell_type):
      self.output.warning(f"{shell_type} not found in container, trying sh...")
      shell_type = "sh"
      if not self.is_shell_exists(container_id, shell_type):
        self.output.error("No shell found in container")
        sys.exit(1)

    self.docker(["exec", "-it", container_id, shell_type], capture_output=False, text=False)

  def exec(self, service: str, command: tuple[str, ...], shell_type: str = "bash"):
    """Execute a command in a container."""
    container_id = self.get_container_id(service)

    # Calculate a relative path for a working directory
    cwd = Path.cwd()
    relative_path = cwd.relative_to(self.project.root_dir) if cwd.is_relative_to(self.project.root_dir) else Path()
    container_dest_path = Path(self.project.container_dir) / relative_path

    self.output.debug(f"Working directory: {container_dest_path}")
    self.output.debug(f"Command: {' '.join(command)}")
    self.output.debug(f"Shell: {shell_type}")

    # Check if the specified shell exists
    if not self.is_shell_exists(container_id, shell_type):
      self.output.debug(f"{shell_type} not found, falling back to sh")
      shell_type = "sh"

    result = self.docker([
      "exec",
      "-e", "COLUMNS",
      "-e", "LINES",
      "-it",
      "-w", str(container_dest_path),
      container_id,
      shell_type, "-ilc",
      " ".join(command)
    ], capture_output=False, text=False)
    if result.returncode != 0:
      self.output.error(f"Command exited with code: {result.returncode}")
      sys.exit(result.returncode)

  def exec_custom(self, command: str, args: List[str]) -> bool:
    """Execute a custom project command if it exists"""
    self.load_project()
    cmd_dir = self.project.dip_dir / "commands"
    if not self.project or not cmd_dir.exists():
      return False

    cmd_file = cmd_dir / command
    if cmd_file.exists() and os.access(cmd_file, os.X_OK):
      cmd = [str(cmd_file), *args]
      self.output.debug(f"Executing custom command: {' '.join(cmd)}")
      subprocess.run(cmd, env=self.project.get_env())
      return True

    return False


  # --------------------------------------
  # Container Management
  # --------------------------------------
  def start(self):
    """Start all containers"""
    self.auto_start_traefik()
    self.output.info("Starting containers...")
    self.compose(["up", "-d"], capture_output=False)
    self.output.success("All containers started successfully")

  def stop(self):
    """Stop all containers"""
    self.output.info("Stopping containers...")
    self.compose(["stop"], capture_output=False)
    self.output.success("All containers stopped")

  def restart(self):
    """start all containers"""
    self.auto_start_traefik()
    self.output.info("Restarting containers...")
    self.compose(["restart"], capture_output=False)
    self.output.success("All containers restarted")

  def build(self, service: Optional[str] = None):
    """Rebuild service containers"""
    if service:
      with self.output.status(f"Building service: {service}..."):
        self.compose(["build", service], capture_output=False)
      self.output.success(f"Service '{service}' built successfully")
    else:
      with self.output.status("Building all services..."):
        self.compose(["build"], capture_output=False)
      self.output.success("All services built successfully")

  def pull(self):
    """Pull latest images"""
    self.output.info("Pulling latest images...")
    self.compose(["pull"], capture_output=False)
    self.output.success("Images pulled successfully")

  def reset(self):
    """Reset containers (stop, remove, start)"""
    self.output.warning("Stopping containers...")
    self.compose(["stop"], capture_output=False)
    self.output.warning("Removing containers...")
    self.compose(["rm", "-f"], capture_output=False)
    self.output.success("Starting containers...")
    self.compose(["up", "-d"], capture_output=False)
    self.output.success("Container reset completed")

  def remove(self):
    """Reset containers (stop, remove, start)"""
    self.output.warning("Removing containers...")
    self.compose(["rm", "-f"], capture_output=False)
    self.output.success("Containers removed")

  # TODO: Needs testing
  def cleanup(self):
    """Remove unused containers/images for this project"""
    self.load_project()
    self.output.warning("Finding stopped containers...")
    result = self.docker([
      "ps", "-a", "-q",
      "--filter", f"name={self.project.project_name}",
      "--filter", "status=exited"
    ])

    stopped = result.stdout.strip().split()
    if stopped:
      self.output.warning("Removing stopped containers...")
      self.docker(["rm", *stopped], capture_output=False)
    else:
      self.output.success("No stopped containers found")

    self.output.warning("Removing dangling images...")
    self.docker(["image", "prune", "-f"], capture_output=False)
    self.output.success("Cleanup completed")

  # TODO: Needs testing
  def prune(self):
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
    self.docker(["system", "prune", "-f"], capture_output=False)

    self.output.warning("Pruning Docker volumes...")
    self.docker(["volume", "prune", "-f"], capture_output=False)

    self.output.success("System prune completed")

  # --------------------------------------
  # Self-update
  # --------------------------------------
  def update(self):
    """Update dip to the latest version."""
    self.output.info("Checking for updates...")

    try:
      # Download update script
      update_script_url = f"https://raw.githubusercontent.com/{config.repo['owner']}/{config.repo['name']}/main/scripts/update.sh"

      self.output.info(f"Downloading update script from: {update_script_url}")

      with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
        update_script = f.name

      urllib.request.urlretrieve(update_script_url, update_script)

      os.chmod(update_script, 0o755)

      self.output.warning("Running update...")
      result = subprocess.run(["/bin/bash", update_script], check=False)

      # Cleanup
      os.remove(update_script)

      if result.returncode == 0:
        self.output.success("Update complete!")
      else:
        self.output.error("Update failed")
        sys.exit(1)

    except Exception as e:
      self.output.error(f"Update failed: {e}")
      sys.exit(1)



  # --------------------------------------
  # Database Management
  # --------------------------------------
  # TODO: Improve to support other drivers and multiple databases
  # TODO: Needs testing
  def db_dump(self, output_path: str):
    """Export database dump"""
    container_id = self.get_container_id("db")

    env_vars = self.project.get_env()
    db_name = env_vars.get('MYSQL_DATABASE')
    db_pass = env_vars.get('MYSQL_ROOT_PASSWORD')

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
  # TODO: Needs testing
  def db_import(self, input_path: str):
    """Import database dump"""
    if not Path(input_path).exists():
      self.output.error(f"File {input_path} not found")
      sys.exit(1)

    container_id = self.get_container_id("db")

    env_vars = self.project.get_env()
    db_name = env_vars.get('MYSQL_DATABASE')
    db_pass = env_vars.get('MYSQL_ROOT_PASSWORD')

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
  def traefik(self, action: str):
    """Manage Traefik proxy"""
    if action == "start":
      self.start_traefik()

    elif action == "stop":
      self.stop_traefik()

    elif action == "status":
      if not self.is_traefik_running():
        self.output.warning("Traefik is not running")
        return

      result = self.docker([
        "ps", "--filter", "name=traefik",
         "--format", "{{.Names}}\t{{.Status}}\t{{.Ports}}"
      ])

      table = Table(title="Traefik Status", box=box.ROUNDED)
      table.add_column("Container", style="cyan")
      table.add_column("Status", style="green")
      table.add_column("Ports", style="blue")

      parts = result.stdout.strip().split('\t')
      if len(parts) >= 2:
        table.add_row(parts[0], parts[1], parts[2] if len(parts) > 2 else "")

      self.output.console.print(table)

    elif action == "restart":
      self.stop_traefik()
      self.start_traefik()

    elif action == "reset":
      self.stop_traefik()
      self.docker(["rm", "traefik"])
      self.start_traefik()

    else:
      self.output.error(f"Unknown traefik command: {action}")
      self.output.console.print("Available: [cyan]start, stop, status, restart[/cyan]")
      sys.exit(1)

  def is_traefik_running(self) -> bool:
    """Check if Traefik is running"""
    result = self.docker(["ps", "--filter", "name=traefik", "--filter", "status=running", "-q"])
    return bool(result.stdout.strip())

  # TODO: Improve error handling
  def check_traefik_network(self):
    try:
      self.docker(
        ['network', 'inspect', "traefik_network"],
        capture_output=True,
        check=True
      )
    except subprocess.CalledProcessError:
      self.docker(["network", "create", "traefik_proxy"])

  def start_traefik(self):
    """Start Traefik proxy"""
    if self.is_traefik_running():
      return

    compose_file: Path = self.config_dir / "traefik" / "docker-compose.yml"

    if not compose_file.exists():
      self.output.error(f"Traefik `docker-compose.yml` file not found: {compose_file}")
      return

    with self.output.status("Starting Traefik proxy..."):
      self.check_traefik_network()
      result = self.docker(["compose", "-f", str(compose_file), "up", "-d"])

      if self.is_traefik_running():
        self.output.success("Traefik started successfully")
      else:
        self.output.error(f"Failed to start Traefik: {result.stderr.strip()}")

  def stop_traefik(self):
    """Stop Traefik proxy"""
    if not self.is_traefik_running():
      self.output.info("Traefik is not running")
      return

    compose_file: Path = self.config_dir / "traefik" / "docker-compose.yml"

    if not compose_file.exists():
      self.output.error(f"Traefik `docker-compose.yml` file not found: {compose_file}")
      return

    with self.output.status("Stopping Traefik proxy..."):
      self.docker(["compose", "-f", str(compose_file), "down"])

    self.output.success("Traefik stopped")

  def auto_start_traefik(self):
    """Auto-start Traefik on Linux"""
    if sys.platform == "linux" and not self.is_traefik_running():
      self.start_traefik()

