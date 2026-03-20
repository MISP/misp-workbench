import logging.config
import os

def setup_logging():
    """Setup logging configuration with environment variable support."""
    # Read log level from environment variable, default to INFO
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()

    # Create a basic logging configuration dictionary
    logging_config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'normal': {
                'format': '%(asctime)s loglevel=%(levelname)-6s logger=%(name)s:%(funcName)s() L%(lineno)-4d %(message)s'
            },
            'detailed': {
                'format': '%(asctime)s loglevel=%(levelname)-6s logger=%(name)s:%(funcName)s() L%(lineno)-4d %(message)s   call_trace=%(pathname)s L%(lineno)-4d'
            }
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'level': log_level,
                'formatter': 'normal',
                'stream': 'ext://sys.stdout'
            },
            'detailed_console': {
                'class': 'logging.StreamHandler',
                'level': log_level,
                'formatter': 'detailed',
                'stream': 'ext://sys.stdout'
            }
        },
        'root': {
            'level': log_level,
            'handlers': ['console']
        }
    }

    logging.config.dictConfig(logging_config)