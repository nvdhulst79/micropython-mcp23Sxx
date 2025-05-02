# micropython-mcp23Sxx

Micropython SPI version of https://github.com/dsiggi/micropython-mcp230xx (I2C).

This is a work in progress, NOT a working driver (yet). This readme is not fully updated yet, consider anything below this as incorrect in regards to this fork!

The mappings between pins and addresses are...

![Pin pull table](http://raspi.tv/wp-content/uploads/2013/07/MCP23017-addresspins1.jpg)

If you wish to use a different address, or a different SPI port than the default then pass that in to the constructor.

The default constructor arguments mean that MCP23S17() is equivalent to MPC23S17(spi=SPI(baudrate=1000000, polarity=0, bits=8, firstbit=SPI.MSB), gpioCS=20, address=0x20).
This way you can choose to use hardware or software SPI, at a speed that you choose. 
Please note that polarity, bits and firstbit should not differ from the default

For example, the following will set the output values of pins 10-15 and read the logic value (True or False) of pins 0-9

```python
import mcp

io = mcp.MCP23S17()

# controls some output pins
outPins = list(range(10,16))
nextVals = {}
for pinNum in outPins:
    io.setup(pinNum, mcp.OUT)
    nextVals[pinNum] = True
io.output_pins(nextVals)

# monitors and prints some input pins
inPins = list(range(0,10))
for pinNum in inPins:
    io.setup(pinNum, mcp.IN)
while True:
    print(io.input_pins(inPins))
```

Example for using interrupts.

```python
from machine import Pin
import mcp

io = mcp.MCP23S17()

# Using PortB(0) and PortB(2) as input
io.setup(8, mcp.IN)
io.setup(10, mcp.IN)

# Enable interrupts for both pins
io.set_interrupt(8, True)
io.set_interrupt(10, True)

# Set the polarity of the INTx-pins to aktiv high
io.configure(interrupt_polarity=True)

# Callback function for the interrupt
def callback(p):
    print("Interrupt captured")
    print("These are the states of the pins:")
    print(io.read_captured_gpio())

# The INTB-pin is connected to GPIO12
int_pin = Pin(12, Pin.IN)
int_pin.irq(trigger=Pin.IRQ_RISING, handler=callback)

```
