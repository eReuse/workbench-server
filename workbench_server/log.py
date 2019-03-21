import logging.config
import pathlib


def log(dir: pathlib.Path = pathlib.Path.home() / 'workbench' / '.settings', name='ws.log'):
    dir.mkdir(parents=True, exist_ok=True)
    """Defines the logging."""
    logging.config.dictConfig({
        'version': 1,
        'formatters': {
            'default': {
                'format': '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
            }
        },
        'handlers': {
            'rotating': {
                'class': 'logging.handlers.RotatingFileHandler',
                'formatter': 'default',
                'filename': str(dir / name),
                'maxBytes': 10 ** 6,
                'backupCount': 3
            }
        },
        'root': {
            'level': 'DEBUG',
            'handlers': ['rotating']
        }
    })
