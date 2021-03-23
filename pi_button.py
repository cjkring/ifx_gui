from gpiozero import Button
from time import sleep
import logging
from app_logging import app_logging
from config import read_config

logger = logger.getLogger(__name__)
app_logging(logger, read_config, logging.INFO, "buttons.log")

def button_on(button):
    logger.info(f'Pressed {button}')
    
def button_held(button): 
    logger.info(f'Held {button}')

def button_off(button):
    logger.info(f'Released {button}')

from numpy import arange
for gpio in [27,23,22,18]:
    try:
        button = Button(int(gpio), hold_time = 0.25, hold_repeat=True)
        button.when_activated = button_on
        button.when_held = button_held
        button.when_deactivated = button_off
    except Exception as e:
        logger.exception(f'exception configuring GPIO {gpio}:')

while True:
    #if button.is_pressed:
    #    print("Pressed")
    #else:
    #    print("Released")
    sleep(1)