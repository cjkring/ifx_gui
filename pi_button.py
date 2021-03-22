from gpiozero import Button
from time import sleep
from os import system

def button_on(button):
    try:
        #print(f'Pressed {button}')
        system('/opt/ifx_gui/bin/toggle_ifx_gui.sh')
        # let things clean up
        sleep(5)
    except Exception as e:
        print(f'toggle ifx gui: {e}')
    
def button_held(button): 
    print(f'Held {button}')

def button_off(button):
    print(f'Released {button}')

#for gpio in [27,23,22,18]:
try:
    button = Button(int(27), hold_time = 1.0, hold_repeat=True)
    button.when_activated = button_on
except Exception as e:
    print(f'GPIO {gpio}: {e}')

while True:
    sleep(0.1)
