
from rich.console import Console
from rich.panel import Panel


class SingletonMeta(type):
  _instances = {}

  def __call__(cls, *args, **kwargs):
    if cls not in cls._instances:
      cls._instances[cls] = super().__call__(*args, **kwargs)
    return cls._instances[cls]

##
# Output utilities with Rich.Console
##
class Output(metaclass=SingletonMeta):
  """Handle formatted output using Rich."""

  def __init__(self, verbose: bool = False, no_color: bool = None):
    # Only initialize once
    if not hasattr(self, '_initialized'):
      self.is_verbose = verbose
      self.colors = not no_color
      self.console = Console(no_color=no_color)
      self.error_console = Console(stderr=True, no_color=no_color)
      self._initialized = True

  def icon(self, icon: str) -> str:
    """Return a formatted icon"""
    c = self.colors
    match icon:
      case "info": return "ℹ" if c else "[i]"
      case "status": return "◌" if c else "[i]"
      case "ok": return "✓" if c else "[ok]"
      case "error": return "✗" if c else "[x]"
      case "warning": return "⚠" if c else "[!]"
      case "debug": return "⚙" if c else "[d]"
    return ""

  def success(self, message: str):
    self.console.print(f"[bold green]{self.icon('ok')} {message}[/bold green]")

  def error(self, message: str):
    self.error_console.print(f"[bold red]{self.icon('error')} {message}[/bold red]")

  def warning(self, message: str):
    self.console.print(f"[bold yellow]{self.icon('warning')} {message}[/bold yellow]")

  def info(self, message: str):
    self.console.print(f"[bold blue]{self.icon('info')}[/bold blue] {message}")

  def debug(self, message: str):
    if self.is_verbose:
      self.console.print(f"[dim]{self.icon('debug')} {message}[/dim]")

  def verbose(self, message: str):
    if self.is_verbose:
      self.console.print(f"[bold]{self.icon('debug')}[/bold] {message}")

  def verbose_panel(self, content: str, title: str = "", border_style: str = "cyan"):
    if self.is_verbose:
      self.console.print(Panel(content, title=title, border_style=border_style, width=80))

  def panel(self, content: str, title: str = "", border_style: str = "cyan"):
    self.console.print(Panel(content, title=title, border_style=border_style))

  def status(self, message: str):
    return self.console.status(f"[bold green]{message}")

  def header(self, message: str):
    self.console.rule(f"[bold cyan]{message}[/bold cyan]")

  def separator(self):
    self.console.print("[dim]" + "-" * 40 + "[/dim]")

