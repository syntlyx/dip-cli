import json
import os
import re
import sys
import urllib.request
import subprocess
import tempfile
from subprocess import CompletedProcess
from pathlib import Path
from typing import Optional, List

from rich.table import Table
from rich.panel import Panel
from rich.tree import Tree
from rich import box

from dip.config import config
from dip.models import DockerContainer, DockerNetwork
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
    self.traefik_dir = self.config_dir / "traefik"

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


  def get_container(self, service: str, no_error: bool = False) -> Optional[DockerContainer]:
    """Get container ID for a service"""
    containers = self.get_containers()
    expected_prefix = f"{self.project.project_name}-{service}"

    for cntr in containers:
      if cntr.service == service and cntr.names.startswith(expected_prefix):
        return cntr

    if not no_error:
      self.output.error(f"Container for service '{service}' not found")
      sys.exit(1)

    self.output.debug(f"No container found for service: {service}")
    return None

  def get_containers(self, running: bool = False) -> list[DockerContainer]:
    self.is_running()
    self.load_project()
    try:
      result = self.compose([
        "ps", "-a", "--format", "json"
      ])
      containers: list[DockerContainer] = []
      for line in result.stdout.strip().split('\n'):
        if not line:
          continue
        data = json.loads(line)
        container = DockerContainer.from_dict(data.get('Service'), data)
        if not running or container.status == 'running':
          containers.append(container)
      return containers

    except subprocess.CalledProcessError as e:
      self.output.error(f"Command failed with exit code {e.returncode}: {e.stderr}")
      return []

  def get_networks(self, project_name: str) -> list[DockerNetwork]:
    """Get all networks for a Docker Compose project."""
    try:
      result = self.docker([
          "network", "ls",
          "--filter", f"label=com.docker.compose.project={project_name}",
          "--format", '{{json .}}'
        ],
        check=True
      )

      networks = []
      for line in result.stdout.strip().split('\n'):
        if line:
          data = json.loads(line)
          networks.append(DockerNetwork.from_dict(data))

      return networks

    except subprocess.CalledProcessError as e:
      self.output.error(f"Error getting networks: {e.stderr}")
      return []
    except json.JSONDecodeError as e:
      self.output.error(f"Error parsing JSON: {e}")
      return []

  def inspect_network(self, network_id_or_name: str) -> Optional[dict]:
    """Get detailed network information."""
    try:
      result = self.docker(["docker", "network", "inspect", network_id_or_name], check=True)
      data = json.loads(result.stdout)
      return data[0] if data else None

    except subprocess.CalledProcessError as e:
      self.output.error(f"Error disconnecting network: {e.stderr}")
    except json.JSONDecodeError as e:
      self.output.error(f"Error disconnecting network: {e}")
    return None

  def disconnect_network(self, network_id_or_name: str):
    try:
      result = self.docker(["ps", "-aq", "--no-trunc", "--filter", f"network={network_id_or_name}"], check=True)
      for container_id in result.stdout.strip().split('\n'):
        self.docker(["network", "disconnect", "-f", network_id_or_name, container_id])
    except subprocess.CalledProcessError as e:
      self.output.error(f"Error disconnecting network: {e.stderr}")
      sys.exit(e.returncode)

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
    containers = self.get_containers()
    if not len(containers):
      self.output.warning("No containers found")
      return

    table = Table(title=f"Project: {self.project.project_name}",
                  title_justify="left",
                  box=box.ROUNDED)
    table.add_column("ID", no_wrap=True)
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Status", style="magenta")
    table.add_column("Ports")

    for contr in containers:
      table.add_row(contr.id, contr.names, contr.status, contr.ports)

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
      container = self.get_container(service)
      self.output.info(f"Showing stats for service: {service}")
      self.docker(["stats", container.id], capture_output=False)
    else:
      self.docker(["stats"], capture_output=False)

  def top(self, service: Optional[str] = None):
    """Show running processes in containers"""
    if service:
      container = self.get_container(service)
      self.output.info(f"Running processes in {service} container:")
      self.docker(["top", container.id], capture_output=False)
    else:
      self.load_project()
      self.output.info(f"Running processes for {self.project.project_name} containers:")
      containers = self.get_containers(True)
      if not len(containers):
        self.output.warning("No running containers found")
        return

      for container in containers:
        name_result = self.docker(["ps", "--format", "{{.Names}}", "-f", f"id={container.id}"])
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
    container = self.get_container(service)
    self.output.verbose(f"Entering {shell_type} in container: {container.service}")
    if not self.is_shell_exists(container.id, shell_type):
      self.output.warning(f"{shell_type} not found in container, trying sh...")
      shell_type = "sh"
      if not self.is_shell_exists(container.id, shell_type):
        self.output.error("No shell found in container")
        sys.exit(1)

    self.docker(["exec", "-it", container.id, shell_type], capture_output=False, text=False)

  def exec(self, service: str, command: list[str], shell_type: str = "bash"):
    """Execute a command in a container."""
    container = self.get_container(service)
    env_vars = self.project.get_env()
    host_uid = env_vars.get('HOST_UID', str(os.getuid()))
    host_gid = env_vars.get('HOST_GID', str(os.getgid()))

    cwd = Path.cwd()
    relative_path = cwd.relative_to(self.project.root_dir) if cwd.is_relative_to(self.project.root_dir) else Path()
    container_dest_path = Path(self.project.container_dir) / relative_path

    self.output.debug(f"Working directory: {container_dest_path}")
    self.output.debug(f"Command: {' '.join(command)}")
    self.output.debug(f"Shell: {shell_type}")

    if not self.is_shell_exists(container.id, shell_type):
      self.output.debug(f"{shell_type} not found, falling back to sh")
      shell_type = "sh"

    result = self.docker([
      "exec", "-e", "COLUMNS", "-e", "LINES",
      "-u", f"{host_uid}:{host_gid}",
      "-it", "-w", str(container_dest_path),
      container.id, shell_type, "-ilc", *command
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

  def remove(self, service: str | None):
    """Reset containers (stop, remove, start)"""
    self.load_project()
    if service is None:
      containers = self.get_containers()

      if not containers:
        self.output.warning("No containers found")
        return

      self.output.warning(f"Removing containers and volumes of {self.project.project_name}?")
      tree = Tree(f"[bold blue]◳ {self.project.project_name}[/bold blue]")
      for contr in containers:
        tree.add(f"[cyan]{contr.names}[/cyan]")
      response = input(f"Continue [y/N] ")

      if response.lower() != 'y':
        self.output.warning("Operation cancelled")
        return

      with self.output.status(f"[yellow bold]Removing project resources...") as task:
        for network in self.get_networks(self.project.project_name):
          task.update(f"[yellow bold]Disconnecting {network.name} network from containers...")
          self.disconnect_network(network.id)
        task.update(f"[yellow bold]Removing containers and volumes of {self.project.project_name}...")
        result = self.compose(["down", "--volumes", "--remove-orphans"])
        if result.returncode != 0:
          self.output.error("Failed to remove project resources: " + result.stderr.strip())
      self.output.success("Project resources removed")
    else:
      container = self.get_container(service)
      self.output.warning(f"Removing container resources: {service}...")
      with self.output.status(f"[yellow bold]Stopping container {service}...") as task:
        result = self.compose(["kill", container.id])
        if result.returncode != 0:
          self.output.error("Failed to stop container: " + result.stderr.strip())
        task.update(f"[yellow bold]Removing container {service}...")
        result = self.docker(["rm", "-vf", container.id])
        if result.returncode != 0:
          self.output.error("Failed to remove container: " + result.stderr.strip())
        task.update(f"[green bold]Container resources removed")
      self.output.success(f"Container resources removed")


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
  def db_dump(self, output_path: Path):
    """Export database dump"""
    container = self.get_container("db")

    env_vars = self.project.get_env()
    db_name = env_vars.get('MYSQL_DATABASE')
    db_pass = env_vars.get('MYSQL_ROOT_PASSWORD')

    if not db_name or not db_pass:
      self.output.error("Database credentials not found in environment")
      sys.exit(1)

    self.output.verbose(f"Database: {db_name}")
    self.output.verbose(f"Container: {container.service}")

    with self.output.status(f"Exporting database '{db_name}' to {output_path}..."):
      with open(output_path, 'w') as f:
        result = subprocess.run([
          "docker", "exec", container.id, "mysqldump",
          "-uroot", f"-p{db_pass}", db_name],
          stdout=f, stderr=subprocess.PIPE
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
  def db_import(self, input_path: Path):
    """Import database dump"""
    if not input_path.exists():
      self.output.error(f"File {input_path} not found")
      sys.exit(1)

    container = self.get_container("db")

    env_vars = self.project.get_env()
    db_name = env_vars.get('MYSQL_DATABASE')
    db_pass = env_vars.get('MYSQL_ROOT_PASSWORD')

    self.output.verbose(f"Database: {db_name}")
    self.output.verbose(f"Container: {container.service}")
    with self.output.status(f"Importing database from {input_path} to '{db_name}'..."):
      # Copy file to container
      self.output.verbose("Copying dump file to container...")
      result = subprocess.run(
        ["docker", "cp", input_path, f"{container.id}:/tmp/import.sql"],
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
        ["docker", "exec", container.id, "sh", "-c", import_cmd],
        capture_output=True
      )

      # Cleanup
      self.output.verbose("Cleaning up temporary file...")
      subprocess.run(
        ["docker", "exec", container.id, "rm", "-f", "/tmp/import.sql"],
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

    compose_file: Path = self.traefik_dir / "docker-compose.yml"

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

    compose_file: Path = self.traefik_dir / "docker-compose.yml"

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

  def traefik_config(self, service: str, domain: str, port: str = '80'):
    """Traefik config"""
    self.get_container(service)

    self.output.info(f"Append this to your [bold]{service}[/bold] service in the [cyan].dip/docker-compose.yml[/cyan]")
    self.output.console.print(
      f"""
    labels:
      - traefik.enable=true
      - traefik.http.routers.{service}.rule=Host(`{domain}`)
      - traefik.http.routers.{service}.entrypoints=websecure
      - traefik.http.routers.{service}.tls=true
      - traefik.http.services.{service}.loadbalancer.server.port={port}
    networks:
      - traefik_proxy
""")
    self.output.warning(f"Stop and start sequence is required:")
    self.output.console.print(
      f"  dip stop\n"
      f"  dip start"
    )

  def mkcert(self, domain: str):
    self.output.info(f"Generating certificate for: [cyan]{domain}[/cyan]")
    domain_filename = domain.replace('*', 'wildcard').replace('.', '-')
    base_domain = domain.replace('*.', '') if '*' in domain else f"www.{domain}"
    certs_dir: Path = self.traefik_dir / "certs"
    certs_dir.mkdir(parents=True, exist_ok=True)
    self.output.info(f"Output directory: {certs_dir}")

    # Certificate chain files
    ca_key_file: Path = certs_dir / "ca-key.pem"
    ca_cert_file: Path = certs_dir / "ca-cert.pem"
    key_file: Path = certs_dir / f"{domain_filename}.key"
    csr_file: Path = certs_dir / f"{domain_filename}.csr"
    cert_file: Path = certs_dir / f"{domain_filename}.crt"
    chain_file: Path = certs_dir / f"{domain_filename}-chain.crt"
    config_file: Path = self.traefik_dir / "dynamic" / f"{domain_filename}.yml"

    # Step 1: Create CA if it doesn't exist
    if not ca_cert_file.exists():
      self.output.info(f"Generating Certificate Authority (CA)")

      result = subprocess.run(
        ["openssl", "genrsa", "-out", ca_key_file, "4096"],
        capture_output=True
      )
      if result.returncode != 0:
        self.output.error(f"Failed to generate CA key: {result.stderr.decode().strip()}")
        sys.exit(1)
      os.chmod(ca_key_file, 0o600)

      result = subprocess.run(
        ["openssl", "req", "-new", "-x509", "-days", "3650",
         "-key", ca_key_file, "-out", ca_cert_file,
         "-subj", "/CN=Local Development CA/O=Development/OU=Certificate Authority"],
        capture_output=True
      )
      if result.returncode != 0:
        self.output.error(f"Failed to generate CA certificate: {result.stderr.decode().strip()}")
        sys.exit(1)

      self.output.success(f"CA Certificate created: [default]{ca_cert_file}")
      self.output.warning(f"Import {ca_cert_file} to your system's trusted root certificates!")
    else:
      self.output.info(f"Using existing CA: {ca_cert_file}")

    # Step 2: Generate server private key
    self.output.info(f"Generating server private key")
    result = subprocess.run(
      ["openssl", "genrsa", "-out", key_file, "2048"],
      capture_output=True
    )
    if result.returncode != 0:
      self.output.error(f"Failed to generate private key: {result.stderr.decode().strip()}")
      sys.exit(1)
    os.chmod(key_file, 0o600)
    self.output.success(f"Private key: [default]{key_file}")

    # Step 3: Create CSR (Certificate Signing Request)
    country = "US"
    state = "NC"
    locality = "Wilmington"

    response = input("Country Name (2 letter code) [US]: ")
    if response:
      country = response.strip()
    response = input("State or Province Name (full name) [NC]: ")
    if response:
      state = response.strip()
    response = input("Locality Name (eg, city) [Wilmington]: ")
    if response:
      locality = response.strip()

    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.cnf') as f:
      tmpcfg: Path = Path(f.name)

    tmpcfg.write_text(f"""[req]
default_bits = 2048
prompt = no
default_md = sha256
distinguished_name = dn

[dn]
C={country}
ST={state}
L={locality}
O=Development
OU=Local Development
CN={domain}
""")

    self.output.info(f"Generating Certificate Signing Request (CSR)")
    result = subprocess.run(
      ["openssl", "req", "-new", "-key", key_file,
       "-out", csr_file, "-config", tmpcfg],
      capture_output=True
    )
    os.remove(tmpcfg)
    if result.returncode != 0:
      self.output.error(f"Failed to generate CSR: {result.stderr.decode().strip()}")
      sys.exit(1)


    # Step 4: Create extensions file for SAN
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.ext') as f:
      tmpext: Path = Path(f.name)

    tmpext.write_text(f"""basicConstraints = CA:FALSE
keyUsage = critical, digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth
subjectAltName = @alt_names

[alt_names]
DNS.1 = {domain}
DNS.2 = {base_domain}
""")

    # Step 5: Sign the certificate with CA
    self.output.info(f"Signing certificate with CA")
    result = subprocess.run(
    ["openssl", "x509", "-req", "-days", "365",
     "-in", csr_file,
     "-CA", ca_cert_file,
     "-CAkey", ca_key_file,
     "-CAcreateserial",
     "-out", cert_file,
     "-extfile", tmpext],
      capture_output=True
    )
    os.remove(tmpext)
    if result.returncode != 0:
      self.output.error(f"Failed to sign certificate: {result.stderr.decode().strip()}")
      sys.exit(1)


    # Clean up CSR (no longer needed)
    if csr_file.exists():
      os.remove(csr_file)

    self.output.success(f"Certificate: [default]{cert_file}")

    # Step 6: Create full chain certificate (server cert + CA cert)
    self.output.info(f"Creating certificate chain")
    with open(chain_file, 'w') as outfile:
      with open(cert_file, 'r') as infile:
        outfile.write(infile.read())
      with open(ca_cert_file, 'r') as infile:
        outfile.write(infile.read())

    self.output.success(f"Full chain certificate: [default]{chain_file}")

    # Step 7: Generate Traefik configuration
    self.output.info(f"Generating Traefik configuration")
    config_file.parent.mkdir(parents=True, exist_ok=True)

    config_file.write_text(f"""# Traefik TLS configuration for {domain}
tls:
  certificates:
    - certFile: /certs/{chain_file.name}
      keyFile: /certs/{key_file.name}
      stores:
        - default

  stores:
    default:
      defaultCertificate:
        certFile: /certs/{chain_file.name}
        keyFile: /certs/{key_file.name}
""")
    self.output.success(f"Traefik config: [default]{config_file}")

    result = subprocess.run(
      ["openssl", "x509", "-in", cert_file,
       "-noout", "-subject", "-issuer", "-dates"],
      capture_output=True, text=True
    )
    certinfo = ''
    if result.returncode == 0:
      certinfo = result.stdout.strip()

    self.output.info(f"Verifying certificate chain")
    result = subprocess.run(
      ["openssl", "verify", "-CAfile", ca_cert_file, cert_file],
      capture_output=True, text=True
    )
    if result.returncode != 0:
      self.output.warning(f"Verification: {result.stderr.strip()}")

    self.output.info(f"Verifying full chain certificate")
    result = subprocess.run(
      ["openssl", "verify", "-CAfile", ca_cert_file, chain_file],
      capture_output=True, text=True
    )
    if result.returncode != 0:
      self.output.warning(f"Full chain verification: {result.stderr.strip()}")

    show_certs = f"""[bold cyan]Certificate Information:[/bold cyan]
{certinfo}

[bold cyan]Location:[/bold cyan] {certs_dir}

[bold cyan]Certificate Authority (CA):[/bold cyan]
[green bold]▶[/green bold] Certificate: {ca_cert_file.name}
[green bold]▶[/green bold] Private Key: {ca_key_file.name}

[bold cyan]Server Certificate:[/bold cyan]
[green bold]▶[/green bold] Certificate: {cert_file.name}
[green bold]▶[/green bold] Chain: {chain_file.name}
[green bold]▶[/green bold] Private Key: {key_file.name}
"""
    self.output.console.print(Panel(
      show_certs,
      title="[bold green]Certificate Generated Successfully[/bold green]",
      border_style="green",
      width=140
    ))

    instructions = f"""
[bold yellow]⚠ IMPORTANT: Install the CA certificate on client devices[/bold yellow]

[green bold]▶ CA Certificate:[/green bold] {ca_cert_file}

[bold]• macOS:[/bold]
  sudo security add-trusted-cert -d -r trustRoot \\
    -k /Library/Keychains/System.keychain \\
    {ca_cert_file}

  Or use Keychain Access GUI:
    1. Import {ca_cert_file}
    2. Double-click → Trust → 'Always Trust'

[bold]• Linux (Ubuntu/Debian):[/bold]
  cd {certs_dir}
  sudo cp {ca_cert_file.name} /usr/local/share/ca-certificates/{domain_filename}.crt
  sudo update-ca-certificates

[bold]• Linux (Fedora/RHEL):[/bold]
  cd {certs_dir}
  sudo cp {ca_cert_file.name} /etc/pki/ca-trust/source/anchors/
  sudo update-ca-trust
"""
    self.output.console.print(Panel(
      instructions,
      title="[bold yellow]Install the CA certificate[/bold yellow]",
      width=140
    ))
