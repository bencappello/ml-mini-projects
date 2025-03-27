import os
import sys
import logging

# Configuration for logging format
logging_str = "[%(asctime)s: %(levelname)s: %(module)s: %(message)s]"

# Directory and file paths for log storage
log_dir = "logs"
log_filepath = os.path.join(log_dir,"running_logs.log")
os.makedirs(log_dir, exist_ok=True)

# Basic logging configuration with a file handler and a stream handler
logging.basicConfig(
    level= logging.INFO,
    format= logging_str,

    handlers=[
        logging.FileHandler(log_filepath), # Log to a file
        logging.StreamHandler(sys.stdout) # Log to the console
    ]
)

# Logger instance with a specific name for the project
logger = logging.getLogger("mlProjectLogger")