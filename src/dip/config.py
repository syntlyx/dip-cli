from dataclasses import dataclass

@dataclass
class Config:
  bin_name = 'dip'

  container_root = '/var/www'

  repo = {
    'owner': 'syntlyx',
    'name': 'dip-cli',
  }

  env_name = {
    'project_name':   'PROJECT_NAME',         #
    'project_root':   'PROJECT_ROOT',         # Was: PROJECT_ROOT_DIR
    'env_file':       'ENV_FILE',             # Was: PROJECT_ENV_PATH
    'dip_dir':        'DIP_DIR',              # Was: PROJECT_DOCKER_DIR
    'container_root': 'CONTAINER_ROOT',       # Was: CONTAINER_DIR
    'host_uid':       'HOST_UID',             #
    'host_gid':       'HOST_GID',             #
    'compose_name':   'COMPOSE_PROJECT_NAME', # DO NOT CHANGE! DOCKER-SYSTEM RESERVED ENV VARNAME
  }

config = Config()
