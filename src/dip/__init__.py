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

__version__ = "2.0.0-alpha.2"
__status__ = "Prototype" # Options: "Development", "Production", "Prototype"

__license__ = "MIT"
__copyright__ = "Copyright, 2025 Alex Sytnyk <opensource@banesbyte.com>"
__maintainer__ = "Alex Sytnyk"
__author__ = "Alex Sytnyk, Artem Taranyuk"
__email__ = "opensource@banesbyte.com"

##
# Imports
##
import argparse
import sys
from pathlib import Path

from dip.config import config
from dip.output import Output
from dip.manager import CliManager

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

  parser.add_argument('--version', action='version', version=f'dip {__version__}')
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

  run_parser = subparsers.add_parser('run', help='Run a custom command')
  run_parser.add_argument('cmd', nargs=argparse.REMAINDER, help='Script filename')

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
  subparsers.add_parser('remove', help='Removes project containers')

  # Monitoring
  subparsers.add_parser('sysinfo', help='Show system information')
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

  Output(args.verbose, args.no_color)
  dip = CliManager(__version__, args.verbose)

  if args.verbose:
    dip.output.debug("Verbose mode enabled")

  ##
  # Commands dont require project
  ##
  if args.command == 'sysinfo':
    dip.sysinfo()

  # Self-update process
  elif args.command == 'update':
    dip.update()

  elif args.command == 'prune':
    dip.prune()

  elif args.command == 'run':
    dip.exec_custom(args.cmd[0], args.cmd[1:])

  ##
  # Traefik management
  ##
  if args.command == 'traefik':
    dip.traefik(args.action)

  ##
  # Commands' execution
  ##
  elif args.command == 'shell':
      dip.shell(args.service, args.shell_type)
  elif args.command == 'bash':
      dip.shell(args.service)
  elif args.command == 'exec':
      dip.exec(args.service, args.cmd, args.shell_type)

  ##
  # Container management
  ##
  elif args.command == 'start':
    dip.start()
  elif args.command == 'stop':
    dip.stop()
  elif args.command == 'restart':
    dip.restart()
  elif args.command == 'build':
    dip.build(args.service)
  elif args.command == 'pull':
    dip.pull()
  elif args.command == 'reset':
    dip.reset()
  elif args.command == 'remove':
    dip.remove()
  elif args.command == 'cleanup':
    dip.cleanup()

  ##
  # Container information
  ##
  elif args.command == 'status':
    dip.status()
  elif args.command == 'logs':
    dip.logs(args.service)
  elif args.command == 'stats':
    dip.stats(args.service if hasattr(args, 'service') else None)
  elif args.command == 'top':
    dip.top(args.service)
  elif args.command == 'health':
    dip.health()

  ##
  # Database management
  ##
  elif args.command == 'db':
    if args.db_action == 'dump':
      dip.db_dump(args.output_path)
    elif args.db_action == 'import':
      dip.db_import(args.input_path)
    else:
      parser.parse_args(['db', '-h'])
# --------------------------------------


def custom_excepthook(exc_type, exc_value, exc_traceback):
  if exc_type == KeyboardInterrupt:
    print("\n\nInterrupted by user")
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
    print("\nInterrupted by user")
    sys.exit(130)
  except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
    sys.exit(1)

