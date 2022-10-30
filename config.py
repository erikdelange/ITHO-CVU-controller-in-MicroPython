# Configuration for cc1101.py and itho.py
#
# These are the values which are dependent on the microcontroller,
# development board, hardware design and ITHO remote used. This
# module connects cc1101.py and itho.py to your setup. Aside from
# these constants no further configuation is required. Most of the
# values are used as default function arguments, so changing them
# after the program has started has no effect.
#
# Copyright 2022 (c) Erik de Lange
# Released under MIT license

CHIP = "Wemos S2 Pico - ESP32S2"  # Readable reminder what you have configured. Has no effect.
DEFAULT_SPI_ID = const(1)  # Default hardware SPI channel ID to use
SPI_ID_LIST = [1]  # List with all possible SPI hardware channel ID's
MISO_PIN_PER_SPI_ID = {"1": 36}  # Pin number of MISO for every SPI channel ID
DEFAULT_SS_PIN = 34  # Default slave select pin. Dependent on your hardware design
DEFAULT_GD02_PIN = 38  # Default pin connected to CC101's GD02 pin. Dependent on your hardware design

# The constants below can be set later, after discovering their values by
# running itho.py

ITHO_DEVICE_TYPE = 22  # Your Itho remote device type, 22 is an Itho RFT remote
ITHO_DEVICE_ID = [116, 233, 94]  # Your Itho remote device id

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
