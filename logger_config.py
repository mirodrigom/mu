import logging
import sys
import os
import codecs

def setup_logging():
    # Create logs directory if it doesn't exist
    log_dir = 'logs'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # Remove existing log file if it exists
    log_file = os.path.join(log_dir, 'game.log')
    if os.path.exists(log_file):
        os.remove(log_file)

    # Get root logger and remove any existing handlers
    root_logger = logging.getLogger()
    
    # Remove all existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Set root logger to DEBUG level
    root_logger.setLevel(logging.DEBUG)
    
    # Create formatter with function name included
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s - %(message)s'
    )
    
    # Create console handler with UTF-8 encoding
    if sys.platform == 'win32':
        # On Windows, use sys.stdout.buffer to write UTF-8
        console_handler = logging.StreamHandler(
            codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
        )
    else:
        console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Create file handler with UTF-8 encoding
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)