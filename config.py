# Configuration for cc1101.py and itho.py
#
# These are the values which are dependent on the microcontroller,
# development board, hardware design and ITHO remote used. This
# module connects cc1101.py and itho.py to your setup. Aside from
# these constants no further configuration is required. Most of the
# values are used as default function arguments, so changing them
# after the program has started has no effect.
#
# Copyright 2022 (c) Erik de Lange
# Released under MIT license

BOARD = "Wemos S2 Pico - ESP32S2"  # Reminder which board you have configured. Has no effect.
SPI_ID_LIST = [1]  # List with all possible SPI hardware channel ID's for your board
MISO_PIN_PER_SPI_ID = {"1": 36}  # Pin number of MISO for every SPI channel ID of your board
BUTTON = 0  # User button on S2 Pico is connected to port 0

SPI_ID = 1  # Hardware SPI channel ID to use for communication with your CC1101
SS_PIN = 34  # Slave select pin connected to CC1101's CSn. Dependent on your hardware design
GD02_PIN = 38  # Pin connected to CC101's GD02 pin. Dependent on your hardware design

# The constants below can be set later, after discovering their values by
# running itho.py via the repl

ITHO_REMOTE_TYPE = 22  # Your Itho remote device type, 22 is an Itho RFT remote
ITHO_REMOTE_ID = (116, 233, 94)  # Your Itho remote device id

# Command bytes for the various commands.
# The default values come from an Itho RFT remote, production year 2021.
# Modify if your remote sends different command bytes.
# Discover these by running itho.py

ITHO_JOIN_BYTES = (31, 201, 12, 99, 34, 248)
ITHO_LEAVE_BYTES = (31, 201, 6, 99, 31, 201)
ITHO_LOW_BYTES = (34, 241, 3, 99, 2, 4)
ITHO_MEDIUM_BYTES = (34, 241, 3, 99, 3, 4)
ITHO_HIGH_BYTES = (34, 241, 3, 99, 4, 4)
ITHO_TIMER1_BYTES = (34, 243, 3, 99, 0, 10)
ITHO_TIMER2_BYTES = (34, 243, 3, 99, 0, 20)
ITHO_TIMER3_BYTES = (34, 243, 3, 99, 0, 30)
