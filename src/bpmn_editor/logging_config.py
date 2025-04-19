# logging_config.py
import logging, sys

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(message)s',
        handlers=[
            logging.FileHandler('app.log', encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )

def setup_connection_logging():
    logger = logging.getLogger('bpmn.connections')
    logger.setLevel(logging.DEBUG)
    # ... configuração adicional
