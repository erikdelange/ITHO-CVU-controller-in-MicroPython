# MicroPython CC1101 driver
#
# Inspired by the CC1101 drivers written in C from:
# https://github.com/letscontrolit/ESPEasyPluginPlayground/
# https://github.com/arjenhiemstra/IthoEcoFanRFT/blob/master/Master/Itho/CC1101.cpp
# https://github.com/SpaceTeddy/CC1101/blob/master/cc1100_raspi.cpp
# https://github.com/SpaceTeddy/CC1101/blob/master/cc1100_raspi.h
#
# Copyright 2021 (c) Erik de Lange
# Released under MIT license

import time

from machine import SPI, Pin

import config  # hardware dependent configuration

CHIP = config.CHIP
SPI_ID = config.DEFAULT_SPI_ID
SPI_ID_LIST = config.SPI_ID_LIST
MISO_PIN_PER_SPI_ID = config.MISO_PIN_PER_SPI_ID
SS_PIN = config.DEFAULT_SS_PIN


class CC1101:
    FIFO_BUFFER_SIZE = const(64)

    # Transfer types
    WRITE_SINGLE_BYTE = const(0x00)
    WRITE_BURST = const(0x40)
    READ_SINGLE_BYTE = const(0x80)
    READ_BURST = const(0xC0)

    # Register types
    CONFIG_REGISTER = const(0x80)
    STATUS_REGISTER = const(0xC0)

    # PATABLE and FIFO address
    PATABLE = const(0x3E)
    TXFIFO = const(0x3F)
    RXFIFO = const(0x3F)
    PA_LowPower = const(0x60)
    PA_LongDistance = (0xC0)

    # FIFO Commands
    TXFIFO_BURST = const(0x7F)  # Burst access to TX FIFO
    TXFIFO_SINGLE_BYTE = const(0x3F)  # Single byte access to TX FIFO
    RXFIFO_BURST = const(0xFF)  # Burst access to RX FIFO
    RXFIFO_SINGLE_BYTE = const(0xBF)  # Single byte access to RX FIFO
    PATABLE_BURST = const(0x7E)  # Power control read/write
    PATABLE_SINGLE_BYTE = const(0xFE)  # Power control read/write

    # Configuration registers
    IOCFG2 = const(0x00)  # GDO2 output pin configuration
    IOCFG1 = const(0x01)  # GDO1 output pin configuration
    IOCFG0 = const(0x02)  # GDO0 output pin configuration
    FIFOTHR = const(0x03)  # RX FIFO and TX FIFO thresholds
    SYNC1 = const(0x04)  # Sync word, high byte
    SYNC0 = const(0x05)  # Sync word, low byte
    PKTLEN = const(0x06)  # Packet length
    PKTCTRL1 = const(0x07)  # Packet automation control
    PKTCTRL0 = const(0x08)  # Packet automation control
    ADDR = const(0x09)  # Device address
    CHANNR = const(0x0A)  # Channel number
    FSCTRL1 = const(0x0B)  # Frequency synthesizer control
    FSCTRL0 = const(0x0C)  # Frequency synthesizer control
    FREQ2 = const(0x0D)  # Frequency control word, high byte
    FREQ1 = const(0x0E)  # Frequency control word, middle byte
    FREQ0 = const(0x0F)  # Frequency control word, low byte
    MDMCFG4 = const(0x10)  # Modem configuration
    MDMCFG3 = const(0x11)  # Modem configuration
    MDMCFG2 = const(0x12)  # Modem configuration
    MDMCFG1 = const(0x13)  # Modem configuration
    MDMCFG0 = const(0x14)  # Modem configuration
    DEVIATN = const(0x15)  # Modem deviation setting
    MCSM2 = const(0x16)  # Main Radio Cntrl State Machine configuration
    MCSM1 = const(0x17)  # Main Radio Cntrl State Machine configuration
    MCSM0 = const(0x18)  # Main Radio Cntrl State Machine configuration
    FOCCFG = const(0x19)  # Frequency Offset Compensation configuration
    BSCFG = const(0x1A)  # Bit Synchronization configuration
    AGCCTRL2 = const(0x1B)  # AGC control
    AGCCTRL1 = const(0x1C)  # AGC control
    AGCCTRL0 = const(0x1D)  # AGC control
    WOREVT1 = const(0x1E)  # High byte Event 0 timeout
    WOREVT0 = const(0x1F)  # Low byte Event 0 timeout
    WORCTRL = const(0x20)  # Wake On Radio control
    FREND1 = const(0x21)  # Front end RX configuration
    FREND0 = const(0x22)  # Front end TX configuration
    FSCAL3 = const(0x23)  # Frequency synthesizer calibration
    FSCAL2 = const(0x24)  # Frequency synthesizer calibration
    FSCAL1 = const(0x25)  # Frequency synthesizer calibration
    FSCAL0 = const(0x26)  # Frequency synthesizer calibration
    RCCTRL1 = const(0x27)  # RC oscillator configuration
    RCCTRL0 = const(0x28)  # RC oscillator configuration
    FSTEST = const(0x29)  # Frequency synthesizer calibration control
    PTEST = const(0x2A)  # Production test
    AGCTEST = const(0x2B)  # AGC test
    TEST2 = const(0x2C)  # Various test settings
    TEST1 = const(0x2D)  # Various test settings
    TEST0 = const(0x2E)  # Various test settings

    # Status registers
    PARTNUM = const(0x30)  # Part number
    VERSION = const(0x31)  # Current version number
    FREQEST = const(0x32)  # Frequency offset estimate
    LQI = const(0x33)  # Demodulator estimate for link quality
    RSSI = const(0x34)  # Received signal strength indication
    MARCSTATE = const(0x35)  # Control state machine state
    WORTIME1 = const(0x36)  # High byte of WOR timer
    WORTIME0 = const(0x37)  # Low byte of WOR timer
    PKTSTATUS = const(0x38)  # Current GDOx status and packet status
    VCO_VC_DAC = const(0x39)  # Current setting from PLL calibration module
    TXBYTES = const(0x3A)  # Underflow and number of bytes in TXFIFO
    RXBYTES = const(0x3B)  # Overflow and number of bytes in RXFIFO
    RCCTRL1_STATUS = const(0x3C)  # Last RC oscillator calibration result
    RCCTRL0_STATUS = const(0xF3)  # Last RC oscillator calibration result

    # Command strobes
    SRES = const(0x30)  # Reset chip
    SFSTXON = const(0x31)  # Enable/calibrate frequency synthesizer
    SXOFF = const(0x32)  # Turn off crystal oscillator
    SCAL = const(0x33)  # Calibrate frequency synthesizer and disable
    SRX = const(0x34)  # Enable RX. Perform calibration first if coming from IDLE and MCSM0.FS_AUTOCAL=1.
    STX = const(0x35)  # Enable TX
    SIDLE = const(0x36)  # Exit RX / TX
    SAFC = const(0x37)  # AFC adjustment of freq synthesizer
    SWOR = const(0x38)  # Start automatic RX polling sequence
    SPWD = const(0x39)  # Enter power down mode when CSn goes high
    SFRX = const(0x3A)  # Flush the RX FIFO buffer. Only issue SFRX in IDLE or RXFIFO_OVERFLOW states.
    SFTX = const(0x3B)  # Flush the TX FIFO buffer. Only issue SFTX in IDLE or TXFIFO_UNDERFLOW states.
    SWORRST = const(0x3C)  # Reset real time clock to Event1 value
    SNOP = const(0x3D)  # No operation. May be used to get access to the chip status byte.

    # Bit fields for chip status byte
    STATUS_CHIP_RDYn = const(0x80)  # Should be low when using SPI interface
    STATUS_STATE = const(0x70)
    STATUS_FIFO_BYTES_AVAILABLE = const(0x0F)  # Bytes available in RX FIFO or bytes free in TX FIFO

    # Masks to retrieve status bit
    BITS_TX_FIFO_UNDERFLOW = const(0x80)
    BITS_RX_BYTES_IN_FIFO = const(0x7F)
    BITS_MARCSTATE = const(0x1F)

    # Marc states
    MARCSTATE_SLEEP = const(0x00)
    MARCSTATE_IDLE = const(0x01)
    MARCSTATE_XOFF = const(0x02)
    MARCSTATE_VCOON_MC = const(0x03)
    MARCSTATE_REGON_MC = const(0x04)
    MARCSTATE_MANCAL = const(0x05)
    MARCSTATE_VCOON = const(0x06)
    MARCSTATE_REGON = const(0x07)
    MARCSTATE_STARTCAL = const(0x08)
    MARCSTATE_BWBOOST = const(0x09)
    MARCSTATE_FS_LOCK = const(0x0A)
    MARCSTATE_IFADCON = const(0x0B)
    MARCSTATE_ENDCAL = const(0x0C)
    MARCSTATE_RX = const(0x0D)
    MARCSTATE_RX_END = const(0x0E)
    MARCSTATE_RX_RST = const(0x0F)
    MARCSTATE_TXRX_SWITCH = const(0x10)
    MARCSTATE_RXFIFO_OVERFLOW = const(0x11)
    MARCSTATE_FSTXON = const(0x12)
    MARCSTATE_TX = const(0x13)
    MARCSTATE_TX_END = const(0x14)
    MARCSTATE_RXTX_SWITCH = const(0x15)
    MARCSTATE_TXFIFO_UNDERFLOW = const(0x16)

    # Bit masks for chip status state
    STATE_IDLE = const(0x00)  # IDLE state
    STATE_RX = const(0x10)  # Receive mode
    STATE_TX = const(0x20)  # Transmit mode
    STATE_FSTXON = const(0x30)  # Fast TX ready
    STATE_CALIBRATE = const(0x40)  # Frequency synthesizer calibration is running
    STATE_SETTLING = const(0x50)  # PLL is settling
    STATE_RXFIFO_OVERFLOW = const(0x60)  # RX FIFO has overflowed
    STATE_TXFIFO_UNDERFLOW = const(0x70)  # TX FIFO has underflowed

    def __init__(self, spi_id=SPI_ID, ss=SS_PIN):
        """ Create a CC1101 object connected to a microcontoller SPI channel

        :param int spi_id: microcontroller SPI channel id
        :param int ss: microcontroller pin number used for slave select (SS)
        """
        if spi_id not in SPI_ID_LIST:
            raise ValueError(f"invalid SPI id {spi_id} for {CHIP}")

        self.miso = Pin(MISO_PIN_PER_SPI_ID[str(spi_id)])
        self.ss = Pin(ss, Pin.OUT)
        self.deselect()
        self.spi = SPI(spi_id, baudrate=8000000, polarity=0, phase=0, bits=8,
                       firstbit=SPI.MSB)  # use default pins for mosi, miso and sclk

    def select(self):
        """ CC1101 chip select """
        self.ss.value(0)

    def deselect(self):
        """ CC1101 chip deselect """
        self.ss.value(1)

    def spi_wait_miso(self):
        """ Wait for CC1101 SO to go low """
        while self.miso.value() != 0:
            pass

    def init(self):
        self.reset()

    def reset(self):
        """ CC1101 reset """
        self.deselect()
        time.sleep_us(5)
        self.select()
        time.sleep_us(10)
        self.deselect()
        time.sleep_us(45)
        self.select()

        self.spi_wait_miso()
        self.write_command(CC1101.SRES)
        time.sleep_ms(10)
        # self.spi_wait_miso()
        self.deselect()

    def write_command(self, command):
        """ Write command strobe

        Command strobes share addresses with the status registers
        (address 0x30 to 0x3F). A command strobe must have the
        burst bit set to 0.

        :param int command: strobe byte
        :return int: status byte
        """
        buf = bytearray((command,))
        self.select()
        self.spi_wait_miso()
        self.spi.write(buf)
        self.deselect()
        return buf[0]

    def write_register(self, address, data):
        """ Write single byte to configuration register

        Note that status registers cannot be written to (as that would be
        a command strobe).

        :param int address: byte address of register
        :param int data: byte to write to register
         """
        buf = bytearray(2)
        buf[0] = address | CC1101.WRITE_SINGLE_BYTE
        buf[1] = data
        self.select()
        self.spi_wait_miso()
        self.spi.write(buf)
        self.deselect()

    def read_register(self, address, register_type=0x80):
        """ Read value from configuration or status register

        Status registers share addresses with command strobes (address 0x30
        to 0x3F). To access a status register the burst bit must be set to 1.
        This is handled by the mask in parameter register_type.

        :param int address: byte address of register
        :param int register_type: C1101.CONFIG_REGISTER (default) or STATUS_REGISTER
        :return int: register value (byte)
        """
        read_buf = bytearray(2)
        write_buf = bytearray(2)
        write_buf[0] = address | register_type
        self.select()
        self.spi_wait_miso()
        self.spi.write_readinto(write_buf, read_buf)

        """ CC1101 SPI/26 Mhz synchronization bug - see CC1101 errata
            When reading the following registers two consecutive reads
            must give the same result to be OK. """
        if address in [CC1101.FREQEST, CC1101.MARCSTATE, CC1101.RXBYTES,
                       CC1101.TXBYTES, CC1101.WORTIME0, CC1101.WORTIME1]:
            value = read_buf[1]
            while True:
                self.spi.write_readinto(write_buf, read_buf)
                if value == read_buf[1]:
                    break
                value = read_buf[1]

        self.deselect()
        return read_buf[1]

    def read_register_median_of_3(self, address):
        """ Read register 3 times and return median value """
        lst = list()
        for _ in range(3):
            lst.append(self.read_register(address))
        lst.sort()
        return lst[1]

    def read_burst(self, address, length):
        """ Read values from consecutive configuration registers

        :param int address: start register address
        :param int length: number of registers to read
        :return bytearray: values read (bytes)
        """
        buf = bytearray(length + 1)
        buf[0] = address | CC1101.READ_BURST
        self.select()
        self.spi_wait_miso()
        self.spi.write_readinto(buf, buf)
        self.deselect()
        return buf[1:]

    def write_burst(self, address, data):
        """ Write data to consecutive registers

        :param int address: start register address
        :param bytearray data: values to write (full array is written)
        """
        buf = bytearray(1)
        buf[0] = address | CC1101.WRITE_BURST
        buf[1:1] = data  # append data
        self.select()
        self.spi_wait_miso()
        self.spi.write(buf)
        self.deselect()

    def receive_data(self, length):
        """ Read available bytes from the FIFO

        :param int length: max number of bytes to read
        :return bytearray: bytes read (can have len() of 0)
        """
        rx_bytes = self.read_register(
            CC1101.RXBYTES, CC1101.STATUS_REGISTER) & CC1101.BITS_RX_BYTES_IN_FIFO

        # Check for
        if (self.read_register(CC1101.MARCSTATE,
                               CC1101.STATUS_REGISTER) & CC1101.BITS_MARCSTATE) == CC1101.MARCSTATE_RXFIFO_OVERFLOW:
            buf = bytearray()  # RX FIFO overflow: return empty array
        else:
            buf = self.read_burst(CC1101.RXFIFO, rx_bytes)

        self.write_command(CC1101.SIDLE)
        self.write_command(CC1101.SFRX)  # Flush RX buffer
        self.write_command(CC1101.SRX)  # Switch to RX state

        return buf

    def send_data(self, data):
        """ Send data

        :param bytearray data: bytes to send (len(data) may exceed FIFO size)
        """
        DATA_LEN = CC1101.FIFO_BUFFER_SIZE - 3

        self.write_command(CC1101.SIDLE)

        # Clear TX FIFO if needed
        if self.read_register(CC1101.TXBYTES, CC1101.STATUS_REGISTER) & CC1101.BITS_TX_FIFO_UNDERFLOW:
            self.write_command(CC1101.SIDLE)
            self.write_command(CC1101.SFTX)

        self.write_command(CC1101.SIDLE)

        length = len(data) if len(data) <= DATA_LEN else DATA_LEN

        self.write_burst(CC1101.TXFIFO, data[:length])

        self.write_command(CC1101.SIDLE)
        self.write_command(CC1101.STX)  # Start sending packet

        index = 0

        if len(data) > DATA_LEN:
            # More data to send
            index += length

            while index < len(data):
                while True:
                    tx_status = self.read_register_median_of_3(
                        CC1101.TXBYTES | CC1101.STATUS_REGISTER) & CC1101.BITS_RX_BYTES_IN_FIFO
                    if tx_status <= (DATA_LEN - 2):
                        break

                length = DATA_LEN - tx_status
                length = len(data) - index if (len(data) -
                                               index) < length else length

                for i in range(length):
                    self.write_register(CC1101.TXFIFO, data[index + i])

                index += length

        # Wait until transmission is finished (TXOFF_MODE is expected to be set to 0/IDLE or TXFIFO_UNDERFLOW)
        while True:
            marcstate = self.read_register(
                CC1101.MARCSTATE, CC1101.STATUS_REGISTER) & CC1101.BITS_MARCSTATE
            if marcstate in [CC1101.MARCSTATE_IDLE, CC1101.MARCSTATE_TXFIFO_UNDERFLOW]:
                break


if __name__ == "__main__":
    # Demo
    rf = CC1101(config.DEFAULT_SPI_ID, config.DEFAULT_SS_PIN)
    rf.init()

    # Read status byte
    status = rf.write_command(CC1101.SNOP)
    print("Status byte", hex(status), bin(status))

    # Read version
    version = rf.read_register(CC1101.VERSION, CC1101.STATUS_REGISTER)
    print("VERSION", hex(version))

    # Prove burst and single register access deliver same results
    burst = rf.read_burst(CC1101.IOCFG2, 3)
    for i in range(len(burst)):
        print(hex(burst[i]), end=' ')
    print()

    for register in (CC1101.IOCFG2, CC1101.IOCFG1, CC1101.IOCFG0):
        print(hex(rf.read_register(register)), end=' ')
    print()
