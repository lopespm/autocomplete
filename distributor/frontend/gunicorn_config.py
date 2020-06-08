"""gunicorn WSGI server configuration."""
from multiprocessing import cpu_count
from os import environ, getenv
from distutils.util import strtobool


bind = '0.0.0.0:' + environ.get('PORT', '8000')

max_requests = 1000

workers = int(getenv('NUM_WORKERS', cpu_count() * 2))
threads = int(getenv('MAX_THREADS', 1))
reload = bool(strtobool(getenv('RELOAD', 'false')))
loglevel = getenv('LOG_LEVEL', 'info')
