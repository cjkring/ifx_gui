# this is based upon the rpi mimimal image
sudo raspi-config # setup keyboard, wifi, pi passord to 'gandalf', hostname to 'gandalf', enable camera, SPI, SSH, disable screen blanking

sudo apt update
sudo apt upgrade
sudo apt install xfce4 
sudo reboot now  # xfce4 should come up
# went into raspi-config to set display resolution
sudo apt install python3 python3-pip git tkinter
sudi apt install libatlas-base-dev
sudo apt install python3-bottleneck python3-matplotlib python3-yaml python3-serial python3-fastavro python3-gpiozero

# validate that the camera work
raspistill -o /tmp/image.png

#set up VNC
sudo raspi-config # enable VNC

#set up ifx_gui
cd /tmp
git clone https://github.com/cjkring/ifx_gui.git
sudo mv ifx_gui /opt
sudo mkdir /var/ifx_gui
sudo chown pi /var/ifx_gui
mkdir /var/ifx_gui/data
mkdor /var/ifx_gui/log
cd /opt/ifx_gui
cp config.template config.yml

#picamera has to be installed via apt to bring in external libraries
sudo apt install python3-picamera

# adafruit TFT display
cd /tmp
sudo apt-get install -y git python3-pip
sudo pip3 install --upgrade adafruit-python-shell click==7.0
git clone https://github.com/adafruit/Raspberry-Pi-Installer-Scripts.git
cd Raspberry-Pi-Installer-Scripts
sudo python3 adafruit-pitft.py --display=28r --rotation=90 --install-type=fbcp

#disable CUPS open port
sudo systemctl disable cups.service
sudo systemctl disable cups-browsed

#disable avahi
sudo systemctl disable avahi-daemon

#check open ports
ss -tulw

#start 

# optional -- set up vscode from your workstation
# start vscode on your mac
# install 'Remote - SSH' extension
# click lower red corner,  select 'Remote SSH: Connect to host'
# input pi IP address, pi user, pi password as appropriate
# open /opt/ifx_gui




