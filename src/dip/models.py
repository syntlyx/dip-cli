from dataclasses import dataclass
from datetime import datetime


@dataclass
class DockerContainer:
  id: str
  names: str
  service: str
  image: str
  state: str
  status: str
  created: datetime
  ports: str = ""

  @classmethod
  def from_dict(cls, service_name: str, data: dict[str, str]) -> 'DockerContainer':
    str_created = data.get('CreatedAt', '').rsplit(' ', 1)[0]
    return cls(
      id=data.get('ID', ''),
      names=data.get('Names', ''),
      service=service_name,
      image=data.get('Image', ''),
      state=data.get('State', ''),
      status=data.get('Status', ''),
      created=datetime.strptime(str_created, "%Y-%m-%d %H:%M:%S %z"),
      ports=data.get('Ports', '')
    )


  def created_date(self, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Get formatted creation date."""
    dt = self.created
    return dt.strftime(format_str) if dt else "Unknown"


@dataclass
class DockerNetwork:
  id: str
  name: str
  driver: str
  scope: str
  ipam: dict
  created: str = ""
  labels: dict = None

  @classmethod
  def from_dict(cls, data: dict) -> 'DockerNetwork':
    return cls(
      id=data.get('ID', ''),
      name=data.get('Name', ''),
      driver=data.get('Driver', ''),
      scope=data.get('Scope', ''),
      ipam=data.get('IPAM', {}),
      created=data.get('CreatedAt', ''),
      labels=data.get('Labels', {})
    )