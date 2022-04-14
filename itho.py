# MicroPython ITHO CVE controller
#
# MicroPython version of the C code found in:
# https://github.com/letscontrolit/ESPEasyPluginPlayground/tree/master/libraries%20_PLUGIN145%20ITHO%20FAN/Itho
#

import time

from machine import Pin

from cc1101 import CC1101

import config


class CC1101MESSAGE:
    def __init__(self):
        self.length = 0
        self.data = bytearray(128)


class ITHOCOMMAND:
    UNKNOWN = const(0)
    JOIN = const(1)
    LEAVE = const(2)
    LOW = const(3)
    MEDIUM = const(4)
    HIGH = const(5)
    TIMER1 = const(6)
    TIMER2 = const(7)
    TIMER3 = const(8)

    # Command bytes as sent by RFT remote
    JOIN_BYTES = config.ITHO_JOIN_BYTES
    LEAVE_BYTES = config.ITHO_LEAVE_BYTES
    LOW_BYTES = config.ITHO_LOW_BYTES
    MEDIUM_BYTES = config.ITHO_MEDIUM_BYTES
    HIGH_BYTES = config.ITHO_HIGH_BYTES
    TIMER1_BYTES = config.ITHO_TIMER1_BYTES
    TIMER2_BYTES = config.ITHO_TIMER2_BYTES
    TIMER3_BYTES = config.ITHO_TIMER3_BYTES

    @classmethod
    def commandbytes(cls, command):
        """ Return commandbytes for command """
        if command == cls.JOIN:
            return cls.JOIN_BYTES
        elif command == cls.LEAVE:
            return cls.LEAVE_BYTES
        elif command == cls.LOW:
            return cls.LOW_BYTES
        elif command == cls.MEDIUM:
            return cls.MEDIUM_BYTES
        elif command == cls.HIGH:
            return cls.HIGH_BYTES
        elif command == cls.TIMER1:
            return cls.TIMER1_BYTES
        elif command == cls.TIMER2:
            return cls.TIMER2_BYTES
        elif command == cls.TIMER3:
            return cls.TIMER3_BYTES
        else:
            return cls.LOW_BYTES

    @classmethod
    def find_command(cls, commmandbytes):
        """" Return command for commandbytes """

        def compare(list1, list2):
            # A check on the last two bytes is sufficient
            if list1[4] == list2[4] and list1[5] == list2[5]:
                return True
            return False

        if compare(commmandbytes, cls.JOIN_BYTES):
            return cls.JOIN
        elif compare(commmandbytes, cls.LEAVE_BYTES):
            return cls.LEAVE
        elif compare(commmandbytes, cls.LOW_BYTES):
            return cls.LOW
        elif compare(commmandbytes, cls.MEDIUM_BYTES):
            return cls.MEDIUM
        elif compare(commmandbytes, cls.HIGH_BYTES):
            return cls.HIGH
        elif compare(commmandbytes, cls.TIMER1_BYTES):
            return cls.TIMER1
        elif compare(commmandbytes, cls.TIMER2_BYTES):
            return cls.TIMER2
        elif compare(commmandbytes, cls.TIMER3_BYTES):
            return cls.TIMER3
        else:
            return cls.UNKNOWN


class ITHOPACKET:
    def __init__(self):
        self.command = ITHOCOMMAND.UNKNOWN  # used for incoming message only
        self.device_type = 0  # used for incoming message only
        self.device_id = bytearray(3)  # used for incoming message only
        self.counter = 0  # used for incoming message only

        self.data_decoded = bytearray(32)
        self.data_decoded_chk = bytearray(32)
        self.data_length = 0

    def print(self):
        print("device type", self.device_type)
        print("  device id", end=' ')
        for i in range(len(self.device_id)):
            print(self.device_id[i], end=' ')
        print()
        print("    command", self.command)

        offset = 7 if self.device_type in [24, 28] else 5
        print("      bytes", end=' ')
        for i in range(offset, offset + 6):
            print(self.data_decoded[i], end=' ')
        print()
        print("  bytes chk", end=' ')
        for i in range(offset, offset + 6):
            print(self.data_decoded_chk[i], end=' ')
        print()
        print("    counter", self.counter)
        print()

    def message_encode(self, message):
        """ Encode this ITHOPACKET (self) into message

        :param CC1101PACKET message: space where to store the encoded message
        :return int: number of bytes encoded
        """
        out_bytecounter = 14
        out_bitcounter = 0
        out_patterncounter = 0
        bit_select = 4
        out_shift = 7

        for i in range(out_bytecounter, len(message.data)):
            message.data[i] = 0

        for databyte in range(self.data_length):
            for _ in range(8):
                if out_bitcounter == 8:
                    out_bytecounter += 1
                    out_bitcounter = 0

                if out_patterncounter == 8:
                    out_patterncounter = 0
                    message.data[out_bytecounter] |= 1 << out_shift
                    out_shift -= 1
                    out_bitcounter += 1
                    message.data[out_bytecounter] |= 0 << out_shift
                    if out_shift == 0:
                        out_shift = 8
                    out_shift -= 1
                    out_bitcounter += 1

                if out_bitcounter == 8:
                    out_bytecounter += 1
                    out_bitcounter = 0

                # Set the even bit
                bit = (self.data_decoded[databyte] &
                       (1 << bit_select)) >> bit_select
                bit_select += 1
                if bit_select == 8:
                    bit_select = 0

                message.data[out_bytecounter] |= bit << out_shift
                out_shift -= 1
                out_bitcounter += 1
                out_patterncounter += 1

                # Set the odd bit (inverse of even bit)
                bit = ~bit & 0b00000001
                message.data[out_bytecounter] |= bit << out_shift
                if out_shift == 0:
                    out_shift = 8
                out_shift -= 1
                out_bitcounter += 1
                out_patterncounter += 1

        # Add closing 1 0 pattern to fill last packet.data byte and ensure DC balance in the message
        if out_bitcounter < 8:
            for i in range(out_bitcounter, 8, 2):
                message.data[out_bytecounter] |= 1 << out_shift
                out_shift -= 1
                message.data[out_bytecounter] |= 0 << out_shift
                if out_shift == 0:
                    out_shift = 8
                out_shift -= 1

        return out_bytecounter

    def message_decode(self, message):
        """ Decode message into this ITHOPACKET (= self)

        :param bytearray message: message to decode
        """
        STARTBYTE = 2  # Relevant data starts 2 bytes after the sync pattern bytes SYNC1/SYNC0 = 179/42

        self.data_length = 0
        len_in_buf = len(message) - STARTBYTE  # Correct for sync byte pos

        while len_in_buf >= 5:
            len_in_buf -= 5
            self.data_length += 2

        if len_in_buf >= 3:
            self.data_length += 1

        out_i = 0
        out_j = 4
        out_i_chk = 0
        out_j_chk = 4
        in_bitcounter = 0

        for i in range(STARTBYTE, len(message)):
            for j in range(7, -1, -1):
                if in_bitcounter in [0, 2, 4, 6]:
                    x = message[i]
                    x = x >> j
                    x = x & 0b00000001
                    x = x << out_j
                    self.data_decoded[out_i] |= x
                    out_j += 1
                    if out_j > 7:
                        out_j = 0
                    if out_j == 4:
                        out_i += 1
                if in_bitcounter in [1, 3, 5, 7]:
                    x = message[i]
                    x = x >> j
                    x = x & 0b00000001
                    x = x << out_j_chk
                    self.data_decoded_chk[out_i_chk] |= x
                    out_j_chk += 1
                    if out_j_chk > 7:
                        out_j_chk = 0
                    if out_j_chk == 4:
                        self.data_decoded_chk[out_i_chk] = ~self.data_decoded_chk[out_i_chk]
                        out_i_chk += 1
                in_bitcounter += 1
                if in_bitcounter > 9:
                    in_bitcounter = 0


class ITHO:
    SEND_TRIES = const(3)

    def __init__(self, spi_id=config.DEFAULT_SPI_ID, ss=config.DEFAULT_SS_PIN, gd02=config.DEFAULT_GD02_PIN):
        """ Create ITHO CVE controller

        :param int spi_id: microcontroller SPI channel id
        :param int ss: microcontroller pin number for slave select (SS)
        :param int gd02: microcontroller pin number connected to port GD02 of the CC1101
        """
        self.gd02 = Pin(gd02, mode=Pin.IN)
        self.rf = CC1101(spi_id=spi_id, ss=ss)
        self.rf.reset()

        self.device_type = config.ITHO_DEVICE_TYPE
        self.device_id = config.ITHO_DEVICE_ID
        self.counter = 0  # 0-255 counter, incremented every remote button press / command sent

    def init_transfer(self, length):
        self.rf.write_command(CC1101.SIDLE)
        time.sleep_us(1)

        self.rf.write_register(CC1101.IOCFG0, 0x2E)
        time.sleep_us(1)
        self.rf.write_register(CC1101.IOCFG1, 0x2E)
        time.sleep_us(1)

        self.rf.write_command(CC1101.SIDLE)
        self.rf.write_command(CC1101.SPWD)
        time.sleep_us(2)

        self.rf.write_command(CC1101.SRES)
        time.sleep_us(1)

        self.rf.write_register(CC1101.IOCFG0, 0x2E)  # High impedance (3-state)
        self.rf.write_register(CC1101.FREQ2, 0x21)  # 00100001  878MHz-927.8MHz
        self.rf.write_register(CC1101.FREQ1, 0x65)  # 01100101
        self.rf.write_register(CC1101.FREQ0, 0x6A)  # 01101010
        self.rf.write_register(CC1101.MDMCFG4, 0x5A)
        self.rf.write_register(CC1101.MDMCFG3, 0x83)
        self.rf.write_register(CC1101.MDMCFG2, 0x00)  # 00000000 2-FSK, no manchester encoding/decoding, no preamble/sync
        self.rf.write_register(CC1101.MDMCFG1, 0x22)  # 00100010
        self.rf.write_register(CC1101.MDMCFG0, 0xF8)  # 11111000
        self.rf.write_register(CC1101.CHANNR, 0x00)  # 00000000
        self.rf.write_register(CC1101.DEVIATN, 0x50)
        self.rf.write_register(CC1101.FREND0, 0x17)  # 00010111 use index 7 in PA table
        self.rf.write_register(CC1101.MCSM0, 0x18)  # 00011000  PO timeout Approx. 146microseconds - 171microseconds, Auto calibrate When going from IDLE to RX or TX (or FSTXON)
        self.rf.write_register(CC1101.FSCAL3, 0xA9)  # 10101001
        self.rf.write_register(CC1101.FSCAL2, 0x2A)  # 00101010
        self.rf.write_register(CC1101.FSCAL1, 0x00)  # 00000000
        self.rf.write_register(CC1101.FSCAL0, 0x11)  # 00010001
        self.rf.write_register(CC1101.FSTEST, 0x59)  # 01011001 For test only. Do not write to this register.
        self.rf.write_register(CC1101.TEST2, 0x81)  # 10000001 For test only. Do not write to this register.
        self.rf.write_register(CC1101.TEST1, 0x35)  # 00110101 For test only. Do not write to this register.
        self.rf.write_register(CC1101.TEST0, 0x0B)  # 00001011 For test only. Do not write to this register.
        self.rf.write_register(CC1101.PKTCTRL0, 0x12)  # 00010010 Enable infinite length packets, CRC disabled, Turn data whitening off, Serial Synchronous mode
        self.rf.write_register(CC1101.ADDR, 0x00)  # 00000000
        self.rf.write_register(CC1101.PKTLEN, 0xFF)  # 11111111  Not used, no hardware packet handling

        self.rf.write_burst(CC1101.PATABLE | CC1101.WRITE_BURST, bytearray(
            (0x6F, 0x26, 0x2E, 0x8C, 0x87, 0xCD, 0xC7, 0xC0)))

        self.rf.write_command(CC1101.SIDLE)
        self.rf.write_command(CC1101.SIDLE)

        self.rf.write_register(CC1101.MDMCFG4, 0x5A)
        self.rf.write_register(CC1101.MDMCFG3, 0x83)
        self.rf.write_register(CC1101.DEVIATN, 0x50)
        self.rf.write_register(CC1101.IOCFG0, 0x2D)  # GDO0_Z_EN_N. When this output is 0, GDO0 is configured as input (for serial TX data).
        self.rf.write_register(CC1101.IOCFG1, 0x0B)  # Serial Clock. Synchronous to the data in synchronous serial mode.

        self.rf.write_command(CC1101.STX)
        self.rf.write_command(CC1101.SIDLE)

        self.rf.write_register(CC1101.MDMCFG4, 0x5A)
        self.rf.write_register(CC1101.MDMCFG3, 0x83)
        self.rf.write_register(CC1101.DEVIATN, 0x50)

        # Itho is using serial mode for transmit. We want to use the TX FIFO with fixed packet length for simplicity.
        self.rf.write_register(CC1101.IOCFG0, 0x2E)
        self.rf.write_register(CC1101.IOCFG1, 0x2E)
        self.rf.write_register(CC1101.PKTCTRL0, 0x00)
        self.rf.write_register(CC1101.PKTCTRL1, 0x00)

        self.rf.write_register(CC1101.PKTLEN, length)

    def finish_transfer(self):
        self.rf.write_command(CC1101.SIDLE)
        time.sleep_us(1)

        # GD00 High impedance (3-state)
        self.rf.write_register(CC1101.IOCFG0, 0x2E)
        # GD01 High impedance (3-state)
        self.rf.write_register(CC1101.IOCFG1, 0x2E)

        self.rf.write_command(CC1101.SIDLE)
        self.rf.write_command(CC1101.SPWD)

    def init_receive(self):
        self.rf.write_command(CC1101.SRES)

        self.rf.write_register(CC1101.TEST0, 0x09)
        self.rf.write_register(CC1101.FSCAL2, 0x00)

        self.rf.write_burst(CC1101.PATABLE | CC1101.WRITE_BURST, bytearray(
            (0x6F, 0x26, 0x2E, 0x7F, 0x8A, 0x84, 0xCA, 0xC4)))

        self.rf.write_command(CC1101.SCAL)
        # wait for calibration to finish
        while self.rf.read_register(CC1101.MARCSTATE, CC1101.STATUS_REGISTER) != CC1101.MARCSTATE_IDLE:
            pass

        self.rf.write_register(CC1101.FSCAL2, 0x00)
        self.rf.write_register(CC1101.MCSM0, 0x18)  # No auto calibrate
        self.rf.write_register(CC1101.FREQ2, 0x21)
        self.rf.write_register(CC1101.FREQ1, 0x65)
        self.rf.write_register(CC1101.FREQ0, 0x6A)
        self.rf.write_register(CC1101.IOCFG0, 0x2E)  # GD00 High impedance (3-state)
        self.rf.write_register(CC1101.IOCFG2, 0x06)  # GD02 Assert when sync word has been sent/received, and de-asserts at end of packet
        self.rf.write_register(CC1101.FSCTRL1, 0x06)
        self.rf.write_register(CC1101.FSCTRL0, 0x00)
        self.rf.write_register(CC1101.MDMCFG4, 0x5A)
        self.rf.write_register(CC1101.MDMCFG3, 0x83)
        self.rf.write_register(CC1101.MDMCFG2, 0x00)  # Enable digital DC blocking filter before demodulator, 2-FSK, Disable Manchester encoding/decoding, No preamble/sync
        self.rf.write_register(CC1101.MDMCFG1, 0x22)  # Disable FEC
        self.rf.write_register(CC1101.MDMCFG0, 0xF8)
        self.rf.write_register(CC1101.CHANNR, 0x00)
        self.rf.write_register(CC1101.DEVIATN, 0x50)
        self.rf.write_register(CC1101.FREND1, 0x56)
        self.rf.write_register(CC1101.FREND0, 0x17)
        self.rf.write_register(CC1101.MCSM0, 0x18)  # No auto calibrate
        self.rf.write_register(CC1101.FOCCFG, 0x16)
        self.rf.write_register(CC1101.BSCFG, 0x6C)
        self.rf.write_register(CC1101.AGCCTRL2, 0x43)
        self.rf.write_register(CC1101.AGCCTRL1, 0x40)
        self.rf.write_register(CC1101.AGCCTRL0, 0x91)
        self.rf.write_register(CC1101.FSCAL3, 0xE9)
        self.rf.write_register(CC1101.FSCAL2, 0x2A)
        self.rf.write_register(CC1101.FSCAL1, 0x00)
        self.rf.write_register(CC1101.FSCAL0, 0x11)
        self.rf.write_register(CC1101.FSTEST, 0x59)
        self.rf.write_register(CC1101.TEST2, 0x81)
        self.rf.write_register(CC1101.TEST1, 0x35)
        self.rf.write_register(CC1101.TEST0, 0x0B)
        self.rf.write_register(CC1101.PKTCTRL1, 0x04)  # No address check, append two bytes with status RSSI/LQI/CRC OK,
        # Infinite packet length mode, CRC disabled for TX and RX, No data whitening, Asynchronous serial mode, Data in on GDO0 and data out on either of the GDOx pins
        self.rf.write_register(CC1101.PKTCTRL0, 0x32)
        self.rf.write_register(CC1101.ADDR, 0x00)
        self.rf.write_register(CC1101.PKTLEN, 0xFF)
        self.rf.write_register(CC1101.TEST0, 0x09)

        self.rf.write_command(CC1101.SCAL)
        # wait for calibration to finish
        while self.rf.read_register(CC1101.MARCSTATE, CC1101.STATUS_REGISTER) != CC1101.MARCSTATE_IDLE:
            pass

        self.rf.write_register(CC1101.MCSM0, 0x18)  # No auto calibrate

        self.rf.write_command(CC1101.SIDLE)
        self.rf.write_command(CC1101.SIDLE)

        # Enable digital DC blocking filter before demodulator, 2-FSK, Disable Manchester encoding/decoding, No preamble/sync
        self.rf.write_register(CC1101.MDMCFG2, 0x00)
        # Serial Data Output. Used for asynchronous serial mode.
        self.rf.write_register(CC1101.IOCFG0, 0x0D)

        self.rf.write_command(CC1101.SRX)

        while self.rf.read_register(CC1101.MARCSTATE, CC1101.STATUS_REGISTER) != CC1101.MARCSTATE_RX:
            pass

        self.init_receive_message()

    def init_receive_message(self):
        self.rf.write_command(CC1101.SIDLE)

        # Set datarate
        self.rf.write_register(CC1101.MDMCFG4, 0x5A)  # Set kBaud
        self.rf.write_register(CC1101.MDMCFG3, 0x83)  # Set kBaud
        self.rf.write_register(CC1101.DEVIATN, 0x50)

        # Set fifo mode with fixed packet length and sync bytes
        # 63 bytes message (sync at beginning of message is removed by CC1101)
        self.rf.write_register(CC1101.PKTLEN, 63)

        # Set fifo mode with fixed packet length and sync bytes
        self.rf.write_register(CC1101.PKTCTRL0, 0x00)
        self.rf.write_register(CC1101.SYNC1, 179)
        self.rf.write_register(CC1101.SYNC0, 42)
        # 16bit sync word / 16bit specific
        self.rf.write_register(CC1101.MDMCFG2, 0x02)
        self.rf.write_register(CC1101.PKTCTRL1, 0x00)

        self.rf.write_command(CC1101.SRX)  # Switch to RX state

        # Wait until RX state is entered
        while True:
            marcstate = self.rf.read_register(
                CC1101.MARCSTATE, CC1101.STATUS_REGISTER) & CC1101.BITS_MARCSTATE
            if marcstate == CC1101.MARCSTATE_RX:
                break
            if marcstate == CC1101.MARCSTATE_RXFIFO_OVERFLOW:
                self.rf.write_command(CC1101.SFRX)  # Flush RX buffer

    def get_new_packet(self):
        """ Receive message and convert into ITHOPACKET

        :return ITHOPACKET: packet received, None if invalid packet was received
        """
        message = self.rf.receive_data(63)
        if len(message) == 63:
            itho_packet = self.parse_message(message)
            self.init_receive_message()
            return itho_packet
        return None

    def parse_message(self, message):
        """ Extract information from message into ITHOPACKET

        :param bytearray message: message to parse
        :return ITHOPACKET: parsed message
        """
        itho_packet = ITHOPACKET()

        itho_packet.message_decode(message)

        itho_packet.device_type = itho_packet.data_decoded[0]
        itho_packet.device_id[0] = itho_packet.data_decoded[1]
        itho_packet.device_id[1] = itho_packet.data_decoded[2]
        itho_packet.device_id[2] = itho_packet.data_decoded[3]
        itho_packet.counter = itho_packet.data_decoded[4]

        commandbytes = list()
        offset = 7 if itho_packet.device_type in [24, 28] else 5
        # collect the 6 command bytes from the packet
        for i in range(offset, offset + 6):
            # command byte must equal check byte for a correct command
            if itho_packet.data_decoded[i] == itho_packet.data_decoded_chk[i]:
                commandbytes.append(itho_packet.data_decoded[i])
            else:
                itho_packet.command = ITHOCOMMAND.UNKNOWN
                break
        else:
            itho_packet.command = ITHOCOMMAND.find_command(commandbytes)

        return itho_packet

    def send_command(self, command):
        """ Send command to ITHO CVE

        :param command int: command to send
        """
        self.counter += 1

        # create message
        if command == ITHOCOMMAND.JOIN:
            message = self.create_message_join()
        elif command == ITHOCOMMAND.LEAVE:
            message = self.create_message_leave()
        else:
            message = self.create_message_command(command)

        tries = 30 if command == ITHOCOMMAND.LEAVE else ITHO.SEND_TRIES
        delay = 4 if command == ITHOCOMMAND.LEAVE else 40

        # send message
        for _ in range(tries):
            self.init_transfer(len(message))
            self.rf.send_data(message)
            self.finish_transfer()
            time.sleep_ms(delay)

    def create_message_command(self, command):
        """ Prepare message for command (except JOIN or LEAVE)

        :param int command: command to send
        :return bytearray: message ready for sending
        """
        itho_packet = ITHOPACKET()
        message = CC1101MESSAGE()

        self.create_message_start(message)

        itho_packet.data_decoded[0] = self.device_type
        itho_packet.data_decoded[1] = self.device_id[0]
        itho_packet.data_decoded[2] = self.device_id[1]
        itho_packet.data_decoded[3] = self.device_id[2]
        itho_packet.data_decoded[4] = self.counter

        command_bytes = ITHOCOMMAND.commandbytes(command)
        # ?? add additional offset of 2 for device types 24 and 28 ??
        for i in range(len(command_bytes)):
            itho_packet.data_decoded[i + 5] = command_bytes[i]

        itho_packet.data_decoded[11] = self.checksum(itho_packet, 11)

        itho_packet.data_length = 12

        message.length = itho_packet.message_encode(message)
        message.length += 1

        message.data[message.length] = 172
        message.length += 1

        for i in range(message.length, message.length + 7):
            message.data[i] = 170

        message.length += 7

        return message.data[:message.length]

    def create_message_join(self):
        """ Prepare message for JOIN command

        :return bytearray: message ready for sending
        """
        itho_packet = ITHOPACKET()
        message = CC1101MESSAGE()

        self.create_message_start(message)

        itho_packet.data_decoded[0] = self.device_type
        itho_packet.data_decoded[1] = self.device_id[0]
        itho_packet.data_decoded[2] = self.device_id[1]
        itho_packet.data_decoded[3] = self.device_id[2]
        itho_packet.data_decoded[4] = self.counter

        command_bytes = ITHOCOMMAND.commandbytes(ITHOCOMMAND.JOIN)
        for i in range(len(command_bytes)):
            itho_packet.data_decoded[i + 5] = command_bytes[i]

        itho_packet.data_decoded[11] = self.device_id[0]
        itho_packet.data_decoded[12] = self.device_id[1]
        itho_packet.data_decoded[13] = self.device_id[2]

        itho_packet.data_decoded[14] = 1
        itho_packet.data_decoded[15] = 16
        itho_packet.data_decoded[16] = 224

        itho_packet.data_decoded[17] = self.device_id[0]
        itho_packet.data_decoded[18] = self.device_id[1]
        itho_packet.data_decoded[19] = self.device_id[2]

        itho_packet.data_decoded[20] = self.checksum(itho_packet, 20)

        itho_packet.data_length = 21

        message.length = itho_packet.message_encode(message)
        message.length += 1

        message.data[message.length] = 202
        message.length += 1

        for i in range(message.length, message.length + 7):
            message.data[i] = 170

        message.length += 7

        return message.data[:message.length]

    def create_message_leave(self):
        """ Prepare message for LEAVE command

        :return bytearray: message ready for sending
        """
        itho_packet = ITHOPACKET()
        message = CC1101MESSAGE()

        self.create_message_start(message)

        itho_packet.data_decoded[0] = self.device_type
        itho_packet.data_decoded[1] = self.device_id[0]
        itho_packet.data_decoded[2] = self.device_id[1]
        itho_packet.data_decoded[3] = self.device_id[2]
        itho_packet.data_decoded[4] = self.counter

        command_bytes = ITHOCOMMAND.commandbytes(ITHOCOMMAND.LEAVE)
        for i in range(len(command_bytes)):
            itho_packet.data_decoded[i + 5] = command_bytes[i]

        itho_packet.data_decoded[11] = self.device_id[0]
        itho_packet.data_decoded[12] = self.device_id[1]
        itho_packet.data_decoded[13] = self.device_id[2]

        itho_packet.data_decoded[14] = self.checksum(itho_packet, 14)

        itho_packet.data_length = 15

        message.length = itho_packet.message_encode(message)
        message.length += 1

        message.data[message.length] = 202
        message.length += 1

        for i in range(message.length, message.length + 7):
            message.data[i] = 170

        message.length += 7

        return message.data[:message.length]

    @staticmethod
    def create_message_start(message):
        for i in range(7):
            message.data[i] = 170

        message.data[7] = 171
        message.data[8] = 254
        message.data[9] = 0
        message.data[10] = 179
        message.data[11] = 42
        message.data[12] = 171
        message.data[13] = 42

    @staticmethod
    def checksum(itho_packet, length):
        value = 0
        for i in range(length):
            value += itho_packet.data_decoded[i]
            value &= 0xFF
        return 0 - value


class ITHOREMOTE:
    def __init__(self, device_type=config.ITHO_DEVICE_TYPE, device_id=config.ITHO_DEVICE_ID):
        self.itho = ITHO()
        self.itho.device_type = device_type
        self.itho.device_id = device_id

    def high(self):
        self.itho.send_command(ITHOCOMMAND.HIGH)

    def medium(self):
        self.itho.send_command(ITHOCOMMAND.MEDIUM)

    def low(self):
        self.itho.send_command(ITHOCOMMAND.LOW)

    def timer10(self):
        self.itho.send_command(ITHOCOMMAND.TIMER1)

    def timer20(self):
        self.itho.send_command(ITHOCOMMAND.TIMER2)

    def timer30(self):
        self.itho.send_command(ITHOCOMMAND.TIMER3)

    def join(self):
        self.itho.send_command(ITHOCOMMAND.JOIN)

    def leave(self):
        self.itho.send_command(ITHOCOMMAND.LEAVE)


if __name__ == "__main__":
    itho = ITHO()

    # For send command demo record adjust device_type and
    # device_id to the values you've just discovered and
    # uncomment the 3 lines below
    # itho.device_type = 22  # Your RFT remote type (or adjust in config.py)
    # itho.device_id = [11, 22, 33]  # Your RFT remote ID (or adjust in config.py)
    # itho.send_command(ITHOCOMMAND.HIGH)  # should be audible

    # Listen for commands
    # Use this to discover the device type and id of your remote and
    # the specific command bytes for the buttons on your remote.
    # Usage: Start this program and press the buttons on your remote.

    print("listening to remote commands")

    itho_has_packet = False

    def itho_check(pin):
        global itho_has_packet
        itho_has_packet = True

    itho.gd02.irq(handler=itho_check, trigger=Pin.IRQ_FALLING)

    itho.init_receive()

    counter = 0

    while True:
        if itho_has_packet is True:
            itho_packet = itho.get_new_packet()
            if itho_packet is not None and itho_packet.command != ITHOCOMMAND.UNKNOWN:
                counter += 1
                print("packet", counter)
                itho_packet.print()

            itho_has_packet = False
