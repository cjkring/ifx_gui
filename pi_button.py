from gpiozero import Button
from time import sleep
import logging
from app_logging import app_logging
from config import read_config
from os import system

logger = logging.getLogger(__name__)
app_logging(logger, read_config(), logging.INFO, "buttons.log")

def button_on(button):
    try:
        logger.info(f'Pressed {button}')
        system('/opt/ifx_gui/bin/toggle_ifx_gui.sh')
        # let things clean up
        sleep(5)
    except Exception as e:
        logger.expection(f'toggle ifx gui')
    
def button_held(button): 
    logger.info(f'Held {button}')

def button_off(button):
    logger.info(f'Released {button}')

#for gpio in [27,23,22,18]:
try:
    button = Button(int(27), hold_time = 1.0, hold_repeat=True)
    button.when_activated = button_on
except Exception as e:
    logger.exception(f'exception configuring GPIO {gpio}:')

while True:
    sleep(0.1)
