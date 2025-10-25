
import os
from pathlib import Path
from typing import Optional, Dict

from dip.config import config
from dip.output import Output

DIR_NAME = f".{config.bin_name}"

##
# Project configuration helper class
##
class ProjectConfig:
  """Handle project-specific configuration"""

  def __init__(self, root: Path):
    self.output = Output()
    self.root_dir: Path = root
    self.dip_dir: Path = root / DIR_NAME
    self.env_file: Path = self.dip_dir / ".env"
    self.default_env_file: Path = self.dip_dir / "default.env"
    self.compose_file: Path = self.dip_dir / "docker-compose.yml"

    self.project_name: Optional[str] = None
    self.container_dir: str = config.container_root
    self.env_name: Dict[str, str] = {}

    if not self.env_file.exists():
      if self.default_env_file.exists():
        try:
          self.env_file.open('w').write(self.default_env_file.read_text())
        except:
          raise RuntimeError(f"Error creating env file: {self.env_file}")
      else:
        raise FileNotFoundError(f"Env file not found: {self.env_file}")

    with open(self.env_file) as f:
      for line in f:
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
          key, value = line.split('=', 1)
          self.env_name[key.strip()] = value.strip()

    self.project_name = self.env_name.get(config.env_name['project_name'])
    if not self.project_name:
      raise ValueError(
        f"Env '{config.env_name['project_name']}' must be set in {self.env_file}"
      )

    container_dir = self.env_name.get(config.env_name['container_root'])
    if container_dir:
      self.container_dir = container_dir
    else:
      self.output.warning(
        f"Env '{config.env_name['container_root']}' is not set, using default path: {self.container_dir}"
      )

    icon = f"[bold green]{self.output.icon('ok')}[/bold green]"
    self.output.verbose_panel(
      content=f"{icon} {config.env_name['project_root']}: {self.root_dir}\n"
              f"{icon} {config.env_name['container_root']}: {self.container_dir}\n"
              f"{icon} {config.env_name['dip_dir']}: {self.dip_dir}\n"
              f"{icon} {config.env_name['env_file']}: {self.env_file}\n",
      title="[bold green]Project Config[/bold green]",
    )

  def get_env(self) -> Dict[str, str]:
    """Get environment variables for docker-compose"""
    env = os.environ.copy()
    env.update(self.env_name)

    env_name = config.env_name
    env.update({
      env_name['project_root']:   str(self.root_dir),
      env_name['project_name']:   str(self.project_name),
      env_name['compose_name']:   str(self.project_name),
      env_name['container_root']: str(self.container_dir),
      env_name['dip_dir']:        str(self.dip_dir),
      env_name['env_file']:       str(self.env_file),
      env_name['host_uid']:       str(os.getuid()),
      env_name['host_gid']:       str(os.getgid()),
    })
    return env


def load_project() -> Optional[ProjectConfig]:
  """Find the project root by looking for the .dip directory"""
  def find_root() -> Optional[Path]:
    current = Path.cwd()
    while current != current.parent:
      if (current / DIR_NAME).is_dir():
        return current
      current = current.parent
    return None

  root = find_root()
  return ProjectConfig(root) if root else None

