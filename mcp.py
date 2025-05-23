# Copyright (c) 2014 Adafruit Industries
# Author: Tony DiCola, ported for Micropython ESP8266 by Cefn Hoile
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
from machine import Pin, SPI

OUT     = 0
IN      = 1
HIGH    = True
LOW     = False

RISING  = 1
FALLING = 2
BOTH    = 3

PUD_OFF = 0
PUD_DOWN= 1
PUD_UP  = 2

class MCP():
    """Base class to represent an MCP23Sxx series GPIO extender.  Is compatible
    with the Adafruit_GPIO BaseGPIO class so it can be used as a custom GPIO
    class for interacting with device.
    """

    def __init__(self, spi=SPI(baudrate=1000000, polarity=0, bits=8, firstbit=SPI.MSB), gpioCS=20, address=0x20):
        self.address = address
        self.spi = spi

        self.cs = Pin(gpioCS, Pin.OUT, value=1)
        # Assume starting in ICON.BANK = 0 mode (sequential access).
        # Compute how many bytes are needed to store count of GPIO.
        self.gpio_bytes = self.NUM_GPIO//8
        # Buffer register values so they can be changed without reading.
        self.iodir = bytearray(self.gpio_bytes)  # Default direction to all inputs.
        self.ipol = bytearray(self.gpio_bytes)  # Default polarity is non-inverted
        self.gppu = bytearray(self.gpio_bytes)  # Default to pullups disabled.
        self.gpio = bytearray(self.gpio_bytes)
        self.intcon = bytearray(self.gpio_bytes)
        self.intcap = bytearray(self.gpio_bytes)
        self.defval = bytearray(self.gpio_bytes)
        self.gpinten = bytearray(self.gpio_bytes)
        self.intf = bytearray(self.gpio_bytes)
        self.iocon = bytearray(self.gpio_bytes)

        # Write current direction and pullup buffer state.
        self.write_iodir()
        self.write_gppu()

    def _validate_pin(self, pin):
        """Promoted to mcp implementation from prior Adafruit GPIO superclass"""
        # Raise an exception if pin is outside the range of allowed values.
        if pin < 0 or pin >= self.NUM_GPIO:
            raise ValueError('Invalid GPIO value, must be between 0 and {0}.'.format(self.NUM_GPIO))

    def writeList(self, register, data):
        """Introduced to match the writeList implementation of the Adafruit I2C _device member"""
        try:
            self.cs(0)                               # Select peripheral.
            self.spi.write(self.address << 1)        # Write address
            self.spi.write(register)                 # Register
            self.spi.write(data)                     # Write data
        finally:
            self.cs(1) 

    def readList(self, register, length):
        """Introduced to match the readList implementation of the Adafruit I2C _device member"""
        rxdata = bytearray(length)
        try:
            self.cs(0)                               # Select peripheral.
            self.spi.write((self.address << 1) | 1)  # Read address
            self.spi.write(register)                 # register
            self.spi.readinto(rxdata, 0x0)           # Read data
        finally:
            self.cs(1) 
        return rxdata

    def setup(self, pin, value):
        """
        Set the input or output mode for a specified pin.  
        
        Mode should be either OUT or IN.
        """
        
        self.setup_pins({pin: value})

    def setup_pins(self, pins):
        """
        Set input or output mode for multiple pins.

        Pins should be a dict of pin name to pin mode (IN/OUT)
        """

        [self._validate_pin(pin) for pin in pins.keys()]
        # Set each pin's input bit. 1 for input, 0 for output
        for pin, value in iter(pins.items()):
            if value == IN:
                self.iodir[int(pin/8)] |= 1 << (int(pin%8))
            elif value == OUT:
                self.iodir[int(pin/8)] &= ~(1 << (int(pin%8)))
            else:
                raise ValueError('Unexpected value.  Must be IN or OUT.')
        self.write_iodir()


    def output(self, pin, value):
        """Set the specified pin the provided high/low value.  Value should be
        either HIGH/LOW or a boolean (True = HIGH).
        """
        self.output_pins({pin: value})

    def output_pins(self, pins):
        """Set multiple pins high or low at once.  Pins should be a dict of pin
        name to pin value (HIGH/True for 1, LOW/False for 0).  All provided pins
        will be set to the given values.
        """
        [self._validate_pin(pin) for pin in pins.keys()]
        # Set each changed pin's bit.
        for pin, value in iter(pins.items()):
            if value:
                self.gpio[int(pin/8)] |= 1 << (int(pin%8))
            else:
                self.gpio[int(pin/8)] &= ~(1 << (int(pin%8)))
        # Write GPIO state.
        self.write_gpio()

    def toggle(self, pin):
        """Toggle the specified pin. Inverting the previous value
        """
        self.toggle_pins([pin])
        
    def toggle_pins(self, pins):
        """Toggle multiple pins specified in the given list
        """
        [self._validate_pin(pin) for pin in pins]
        for pin in pins:
            self.gpio[int(pin/8)] ^= 1 << (int(pin%8))  # XOR the pin value
        # Write GPIO state.
        self.write_gpio()

    def input(self, pin, read=True):
        """Read the specified pin and return HIGH/True if the pin is pulled
        high, or LOW/False if pulled low.
        """
        return self.input_pins([pin], read)[0]

    def input_pins(self, pins, read=True):
        """Read multiple pins specified in the given list and return list of pin values
        HIGH/True if the pin is pulled high, or LOW/False if pulled low.
        """
        [self._validate_pin(pin) for pin in pins]
        if read:
            # Get GPIO state.
            self.read_gpio()
        # Return True if pin's bit is set.
        return [(self.gpio[int(pin/8)] & 1 << (int(pin%8))) > 0 for pin in pins]


    def pullup(self, pin, enabled):
        """Turn on the pull-up resistor for the specified pin if enabled is True,
        otherwise turn off the pull-up resistor.
        """
        self.pullup_pins({pin: enabled})

    def pullup_pins(self, pins):
        """
        Turn on the pull-up resistor for multiple pins if enabledd is TRUE
        """

        [self._validate_pin(pin) for pin in pins.keys()]
        for pin, enabled in iter(pins.items()):
            if enabled:
                self.gppu[int(pin/8)] |= 1 << (int(pin%8))
            else:
                self.gppu[int(pin/8)] &= ~(1 << (int(pin%8)))
        self.write_gppu()

    def polarity(self, pin, invert):
        """Set the polarity of the pin. The inverted value will be on the output when True
        """
        self.polarity_pins({pin: invert})

    def polarity_pins(self, pins):
        """
        Set the polarity for multiple pins.
        """

        [self._validate_pin(pin) for pin in pins.keys()]
        for pin, invert in iter(pins.items()):
            if invert:
                self.ipol[int(pin/8)] |= 1 << (int(pin%8))
            else:
                self.ipol[int(pin/8)] &= ~(1 << (int(pin%8)))
        self.write_ipol()

    def read_gpio(self):
        self.gpio = self.readList(self.GPIO, self.gpio_bytes)

    def write_gpio(self, gpio=None):
        """Write the specified byte value to the GPIO register.  If no value
        specified the current buffered value will be written.
        """
        if gpio is not None:
            self.gpio = gpio
        self.writeList(self.GPIO, self.gpio)

    def write_iodir(self, iodir=None):
        """Write the specified byte value to the IODIR register.  If no value
        specified the current buffered value will be written.
        """
        if iodir is not None:
            self.iodir = iodir
        self.writeList(self.IODIR, self.iodir)

    def write_gppu(self, gppu=None):
        """Write the specified byte value to the GPPU register.  If no value
        specified the current buffered value will be written.
        """
        if gppu is not None:
            self.gppu = gppu
        self.writeList(self.GPPU, self.gppu)

    def write_ipol(self, ipol=None):
        """Write the specified byte value to the IPOL register. If no value
        specified the current buffered value will be written.
        """
        if ipol is not None:
            self.ipol = ipol
        self.writeList(self.IPOL, self.ipol)

    def set_interrupt(self, pin, interrupt_enable: bool, defval: bool=False, defval_value: bool=False):
        """
        Set the interrupt mode for a specified pin.
        interrupt_enable: true or false - enable or disable the interrupt feature
        defval: true or false - Interrupt from DEFVAL register or pin change
        defval_value: 0 or 1 - Value for the DEFVal register when using defval
        """
        self._validate_pin(pin)
        # Set bit to 1 for interrupt on or 0 for off
        if interrupt_enable:
            self.gpinten[int(pin/8)] |= 1 << (int(pin%8))
        else:
            self.gpinten[int(pin/8)] &= ~(1 << (int(pin%8)))

        if defval and defval_value:
            self.defval[int(pin/8)] |= 1 << (int(pin%8))
        elif defval and not defval_value:
            self.defval[int(pin/8)] &= ~(1 << (int(pin%8)))

        if defval:
            self.intcon[int(pin/8)] |= 1 << (int(pin%8))

        self.write_gpinten()
        self.write_defval()
        self.write_intcon()

    def write_intcon(self, intcon=None):
        """Write the specified byte value to the INTCON register.  If no value
        specified the current buffered value will be written.
        """
        if intcon is not None:
            self.intcon = intcon
        self.writeList(self.INTCON, self.intcon)

    def write_defval(self, defval=None):
        """Write the specified byte value to the DEFVAL register.  If no value
        specified the current buffered value will be written.
        """
        if defval is not None:
            self.defval = defval
        self.writeList(self.DEFVAL, self.defval)

    def write_gpinten(self, gpinten=None):
        """Write the specified byte value to the GPINTEN register.  If no value
        specified the current buffered value will be written.
        """
        if gpinten is not None:
            self.gpinten = gpinten
        self.writeList(self.GPINTEN, self.gpinten)

    def read_interrupt_gpio(self):
        '''
        Reads the pinnumber witch caused the interrupt from the INTF-register
        '''
        self.intf = self.readList(self.INTF, self.gpio_bytes)
     
        pin = 0
        second_Byte = False
        for i in self.intf:
            while True:
                if i <= 0:
                    break
                elif i & 1 == 1:
                    break
                i = i >> 1
                pin += 1
            if not second_Byte:
                pin += 8
                second_Byte = True

        return pin

    def read_captured_gpio(self):
        '''
        Read the states of the gpios in the moment when the interrupt was captured from the INTCAP-register.
        Returns a dict with all pins and thier states
        '''
        self.intcap = self.readList(self.INTCAP, self.gpio_bytes)

        states = dict()
        second_Byte = False
        for s in self.intcap:
            for i in range(0, 8):
                if s & 1 == 1:
                    if second_Byte:
                        states[i + 8] = True
                    else:
                        states[i] = True
                else:
                    if second_Byte:
                        states[i + 8] = False
                    else:
                        states[i] = False
                s = s >> 1
            second_Byte = True

        return states

    def configure(self, int_mirror: bool=False, opendrain: bool=False, interrupt_polarity: bool=False, hardware_address: bool=False, disable_slewrate: bool=False):
        """
        Configures the IOCON register
        int_mirror: true or false - Mirror the INTx Pins or not
        opendrain: true or false - Interrupt pins are Open-drain output or Actice driver output
        interrupt_polarity: true or false - INT pin is active high or low
        """
        if interrupt_polarity:
            self.iocon[0] |= 1 << 1
            self.iocon[1] |= 1 << 1
        else:
            self.iocon[0] &= ~(1 << 1)
            self.iocon[1] &= ~(1 << 1)

        if opendrain:
            self.iocon[0] |= 1 << 2
            self.iocon[1] |= 1 << 2
        else:
            self.iocon[0] &= ~(1 << 2)
            self.iocon[1] &= ~(1 << 2)

        if hardware_address:
            self.iocon[0] |= 1 << 3
            self.iocon[1] |= 1 << 3
        else:
            self.iocon[0] &= ~(1 << 3)
            self.iocon[1] &= ~(1 << 3)

        if disable_slewrate:
            self.iocon[0] |= 1 << 4
            self.iocon[1] |= 1 << 4
        else:
            self.iocon[0] &= ~(1 << 4)
            self.iocon[1] &= ~(1 << 4)

        if int_mirror:
            self.iocon[0] |= 1 << 6
            self.iocon[1] |= 1 << 6
        else:
            self.iocon[0] &= ~(1 << 6)
            self.iocon[1] &= ~(1 << 6)

        # bit 5 is SEQOP, we keep this 0, since this affects how PORTB is accessed
        # bit 7 is BANK, we keep this 0, since this affects the register adresses

        self.write_iocon()

    def write_iocon(self, iocon=None):
        """Write the specified byte value to the IOCON register.  If no value
        specified the current buffered value will be written.
        """
        if iocon is not None:
            self.iocon = iocon
        self.writeList(self.IOCON, self.iocon)



class MCP23S17(MCP):
    """MCP23S17-based GPIO class with 16 GPIO pins."""
    # Define number of pins and register addresses.
    NUM_GPIO = 16
    IODIR    = 0x00 # Pin Input or Output register
    IPOL     = 0x01 # Polarity register
    GPIO     = 0x12
    GPPU     = 0x0C # Pin Pullup register
    INTCON   = 0x08 # Interrupt-on-Change Control Register
    GPINTEN  = 0X04 # Interrupt-on-Change Pins
    DEFVAL   = 0x06 # Default Value Register
    IOCON    = 0x0A # I/O Expander Configuration Register
    INTF     = 0x0E # Interrupt Flag Register
    INTCAP   = 0x10 # Interrupt Captured Value For Port Register


class MCP23S08(MCP):
    """MCP23S08-based GPIO class with 8 GPIO pins."""
    # Define number of pins and register addresses.
    NUM_GPIO = 8
    IODIR    = 0x00 # Pin Input or Output Register
    IPOL     = 0x01 # Polarity register
    GPIO     = 0x09
    GPPU     = 0x06 # Pin Pullup register
    INTCON   = 0x04 # Interrupt-on-Change Control Register
    GPINTEN  = 0X02 # Interrupt-on-Change Pins
    DEFVAL   = 0x03 # Default Value Register
    IOCON    = 0x05 # I/O Expander Configuration Register
    INTF     = 0x07 # Interrupt Flag Register
    INTCAP   = 0x08 # Interrupt Captured Value For Port Register

if __name__=="__main__":
    io = MCP23S17()
    io.setup(3,IN)
    io.setup(0,OUT)
    io.output(0,HIGH)
    print(io.input(3))