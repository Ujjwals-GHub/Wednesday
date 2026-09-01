import logging
from logging.handlers import RotatingFileHandler

def get_logger():
    """
    Sets up a customized logger with log rotation and a maximum file size.
    """
    logger = logging.getLogger("Wednesday")
    
    # Prevent adding multiple handlers if the module is imported multiple times
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        
        # --- LOG ROTATION SETTINGS ---
        # maxBytes: 1 * 1024 * 1024 = 1 Megabyte
        # backupCount: Keep up to 3 backup files (.log.1, .log.2, .log.3) before deleting the oldest
        file_handler = RotatingFileHandler(
            'wednesday_debug.log', 
            maxBytes=1*1024*1024, 
            backupCount=3
        )
        
        # Define the exact format we want the logs to look like
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        
        # Attach the handler to our custom logger
        logger.addHandler(file_handler)
        
        # Prevent our logs from bubbling up to the root logger (keeps terminal clean)
        logger.propagate = False

    return logger