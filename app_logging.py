import logging
from logging.handlers import RotatingFileHandler
import sys

# this enforces consistent logging across all processes
def app_logging(logger, config,level,logfile):
    logdir = config['app']['log']
    handler = RotatingFileHandler(f'{logdir}/{logfile}',maxBytes=10000,backupCount=5)
    handler.setLevel(level)
    formatter = logging.Formatter('%(levelname)s: %(asctime)s: %(name)s: %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
