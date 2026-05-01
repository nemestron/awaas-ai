import logging
import sys

def setup_logger():
    """Configures structured, production-grade logging for Awaas AI."""
    logger = logging.getLogger("awaas_ai")
    
    # Prevent duplicate handlers if called multiple times
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        
        # Console Handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)
        
        logger.addHandler(console_handler)
        
    return logger

# Initialize the global logger
logger = setup_logger()