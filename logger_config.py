import logging
import sys
import os

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
    root_logger.setLevel(logging.DEBUG)  # Changed from INFO to DEBUG
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create console handler (can keep this at INFO level if you want less console output)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Create file handler (set to DEBUG to catch all messages)
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)  # This will catch debug messages
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)