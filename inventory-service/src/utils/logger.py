import logging
from pythonjsonlogger import jsonlogger
import sys

def get_logger(name: str) -> logging.Logger:
    """
    Retrieves or creates a JSON-formatted logger.
    """
    logger = logging.getLogger(name)
    
    # Check if handlers exist to prevent duplicate log entries when 
    # the logger is imported in multiple files across the service.
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        
        # Output logs directly to standard output (terminal/console)
        handler = logging.StreamHandler(sys.stdout)
        
        # Enforce JSON formatting with critical timestamps and module names
        formatter = jsonlogger.JsonFormatter(
            fmt='%(asctime)s %(levelname)s %(name)s %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        # Prevent logs from propagating to the root logger
        logger.propagate = False
        
    return logger