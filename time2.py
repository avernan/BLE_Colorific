# Smart Bulb Time2 Bulb Control With Bluez
# Author: Tony DiCola
# Author: (Time2 adaptation) Stefano Guazzotti
#
# This script will cycle a Time2 Bulb Bluetooth Low Energy light bulb
# through a rainbow of different hues.
#
# Dependencies:
# - You must install the pexpect library, typically with
#   'sudo pip install pexpect'.
# - You must have bluez installed and gatttool in your path (copy it from the
#   attrib directory after building bluez into the /usr/bin/ location).
#
# License: Released under an MIT license: http://opensource.org/licenses/MIT
import colorsys
import math
import sys
import time

import pexpect
import random
import signal

# Configuration values.
HUE_RANGE  = (0.0, 1.0)  # Tuple with the minimum and maximum hue values for a
                         # cycle. Stick with 0 to 1 to cover all hues.
SATURATION = 1.0         # Color saturation for hues (1 is full color).
VALUE      = 1.0         # Color value for hues (1 is full value).
CYCLE_SEC  = 5.0         # Amount of time for a full cycle of hues to complete.
SLEEP_SEC  = 0.05        # Amount of time to sleep between loop iterations.

# Get bulb address from command parameters.
if len(sys.argv) != 2:
    print 'Error must specify bulb address as parameter!'
    print 'Usage: sudo python time2.py <bulb address>'
    print 'Example: sudo python time2.py 5C:31:3E:F2:16:13'
    sys.exit(1)
bulb = sys.argv[1]


def signal_handler(signal, frame):
    """
    Handle Ctrl-C signal by returning the bulb to white mode with previous
    settings
    """
    print
    print('Bringing the bulb back to white mode on previous settings!')
    back_line = 'char-write-cmd 0x0021 aa0afc3a86010d060280808080808e3f0d'
    gatt.sendline(back_line)
    print('Disconnecting from bulb')
    gatt.send('disconnect')
    gatt.send('exit')
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)

# Run gatttool interactively.
gatt = pexpect.spawn('gatttool -I')

# Connect to the device.
gatt.sendline('connect {0}'.format(bulb))
gatt.expect('Connection successful')

# Setup range of hue value and start at minimum hue.
hue_min, hue_max = HUE_RANGE
hue = hue_min

# Build command in decimal form as a list
# First 9 fixed bytes
cmd = [170, 10, 252, 58, 134, 1, 13, 6, 1]
# Then 3 color bytes
cmd += [0, 0, 0]
# Then two more fixed bytes
cmd += [128, 128]
# Then a random byte
cmd.append(int(random.random() * 255))
# Then the checksum
cmd.append(sum(cmd[1:]) + 85)
# Then the last fixed byte
cmd.append(13)

# Enter main loop.
print 'Press Ctrl-C to quit.'
last = time.time()
while True:
    # Get amount of time elapsed since last update, then compute hue delta.
    now = time.time()
    hue_delta = (now - last) / CYCLE_SEC * (hue_max - hue_min)
    hue += hue_delta
    # If hue exceeds the maximum wrap back around to start from the minimum.
    if hue > hue_max:
        hue = hue_min + math.modf(hue)[0]
    # Compute 24-bit RGB color based on HSV values.
    cmd[9:12] = map(lambda x: int(x * 255.0),
                    colorsys.hsv_to_rgb(hue, SATURATION,
                                        VALUE))
    # Generate random value
    cmd[14] = int(random.random() * 255)
    # Calculate checksum and only keep rightmost byte
    cmd[15] = (sum(cmd[1:15]) + 85) % 256

    # The command string is obtained by converting each number in the `cmd`
    #   list to HEX format and linking them together as a single string.
    line = ('char-write-cmd 0x0021 ' +
            ''.join(['{0:02X}'.format(el) for el in cmd]))
    # Set light color by sending color change packet over BLE.
    gatt.sendline(line)
    # Wait a short period of time and setup for the next loop iteration.
    time.sleep(SLEEP_SEC)
    last = now
