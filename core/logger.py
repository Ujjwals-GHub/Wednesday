import logging
from logging.handlers import RotatingFileHandler

def get_logger():
    """
    Configures and returns a rotating file logger for the application.
    Ensures singleton handler attachment to prevent duplicate log entries.
    """
    logger = logging.getLogger("Wednesday")
    
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        
        file_handler = RotatingFileHandler(
            'wednesday_debug.log', 
            maxBytes=1*1024*1024, 
            backupCount=3,
            encoding='utf-8'
        )
        
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        logger.propagate = False

    return logger
