# Chinese JP e-Scooter ESC to LCD serial protocol decoding

## Overview

Most e-Scooters and other Electric Vehicles have some form of Electronic Speed Controller (ESC)
which is responsible for delivering a power signal that will spin motors at the speed desired 
by the user. The most common type of motors today are of the BLDC type (Brushless DC motors),
which are typically driven by a 3-phase current. 

For these BLDC motors, the ESC needs to be able to generate an accurately timed 3-phase signal 
that varies depending on the position of the shaft and the required torque. It is therefore a 
relatively complex  device which besides having to handle large amounts of power, it needs to 
perform very fast switching of the current and operate in a closed loop. 

Normally in order to estimate the position of the shaft, some kind of resolver is required. 
One of the methods consists of measuring the output from the unpowered phase. When one of the 
stator coils crosses a magnetic pole, a current pulse can be measured, therefore providing 
feedback on the motor position. This is not however a very reliable method, as when the motor 
is stopped, it is not possible to determine its position. This is because there is no induced 
current when a magnet is stationary relative to a coil. BLDC motors using this approach will
normally start "blindly" with low torque, and as soon as a signal is picked up by the unpowered
phase, these will readjust the timings and continue at the desired torque. This method is
good enough for applications that don't require full torque at zero RPM (e.g airplanes, helicopters,
boats), but is inadequate where motors need to drive wheels and provide torque from stand still.
In this case an external sensor is required. The cheapest and most common approach used in e-Scooters
and other EV's consists of adding Hall Effect sensors to the motor stators. Depending on where
the magnetic poles are located relative to these sensors, a very linear response is obtained.
This provides a very good position estimation, regardless if the shaft is moving or not.

There are several manufacturers producing ESC's for EV's in China, and normally there is very
little technical information provided by these, other that the bare minimum required for 
installation and usage. This makes it a challenge for example to understand which parts can
be used with which ESC's.

Taking that into account, and being personally a owner of an e-Scooter, I decided to dig
further and obtain answers in the first person, to some of the curiosities I had about how
the LCD/thumb throttle unit talks to the ESC and vice-versa.


## Hardware description

The JP ESC (the target of this project), consists of a BLDC controller for e-Scooters,
that can operate at 60 Volts (67.2 Volts max - on a fully charged battery), and drive a 
max current of 45 Amps according to the label on the case. 

![JP ESC](/docs/esc/jp_esc_60v_45a.jpg)

I found however the same model advertised in Alibaba, and there is the indication that 
it is rated for 37 Amps, and the customer (scooter manufacturer?) has the option of 
requesting the labels to be printed with the 45 Amps indication.

This scooter is provided with a master ESC which drives the rear motor, and a almost
identical "slave" ESC which drives the front motor. There is a matching LCD unit 
(probably from JP as well), which is physically very similar to other units of this kind, 
for example the QS-S4.

![JP LCD](/docs/esc/jp_lcd.jpg)

Opening a cover on the rear of the unit reveals a 6-pin connector:

![JP LCD Connector](/docs/esc/jp_lcd_connector.jpg)

By doing some probing and checking labels on the PCB silkscreen
I was able to determine the purpose of each pin, which is basically:

 * Red - 60 Volt positive input (P+);
 * Orange - 60 Volt output (when turned on) (DMS);
 * Black - GND (P-);
 * Green - Hall Effect sensor output (HE);
 * Yellow - RX;
 * Blue - TX;

I learned that this unit has a Hall effect sensor for determining the position of the 
throttle lever. The latter has a magnet that is moved relative to the sensor. Depending
on the pole and distance of the magnet, the sensor will output a voltage between 1 and
4 Volts approximately. This sensor is connected directly to this green output pin,
and the LCD unit does not appear to do anything this this signal internally.

The TX and RX pins correspond to the serial (RS-232) communication between the LCD and the ESC.
Data is transmitted at 1200 bps, 8-bits, no parity, and 1 stop bit.

From what I could determine it is used for:

 *  sending settings (the P-settings which are permanently stored on the LCD) to the ESCs.
    These settings are sent constanty (several times per second) in each frame sent to
    the ESC;
 *  receiving status information from the ESC. So far I could determine that one frame
    contains information such as: rear wheel speed (a value proportional to it), presence
    of power applied to the rear motor, and brakes status. There are more values which
    are yet to be identified.

At the moment it is still unclear how the gear information (gears 1, 2 and 3) is sent to 
the ESC.

## P-settings description

Some scooter parameters are configurable via the LCD display via what is commonly refered
as P-settings. These can be accessed by pressing both buttons (power and mode) on the
LCD unit for a few seconds. The using can then navigate up and down on the settings by
pressing on power or mode respectively. 

In order to change a setting, the power button needs to be pressed for a few seconds, and 
once the value is blinking, it can be changed by pressing either button to change the
value of the setting.

My e-Scooter (a Laotie Ti30) has this LCD / ESC installed. There are ten P-settings with
the following factory values:

```
P00 - Wheel diameter: 11
P01 - Voltage cutoff: 51.1
P02 - Number of magnets: 15
P03 - Signal selection (read only): 1
P04 - Distance units (Km/h = 0 or Miles/h = 1): 0
P05 - Pedal assist (off = 0, on = 1): 0
P06 - Cruise control (off = 0, on = 1): 0
PO7 - Soft/hard start (off = 0, on = 1): 0
P08 - Performance (0-100%): 100
P09 - EABS (0-2): 2
```

## Protocol details

Each frame (transmitted by either the ESC or the LCD) is composed of 15 bytes, where 
the last byte corresponds to the checksum (XOR) of the previous bytes. 

The frames have the following structure:

1. LCD to ESC:

Example:

```
01 03 00 00 00 85 00 46 00 80 02 00 00 00 43
...
01 03 10 00 00 55 00 46 00 80 02 00 00 00 83
```

Structure:

```
B00 (01) - Fixed
B01 (03) - Fixed
B02 (00) - Sequence (00, 01, 02, ..., FF)
B03 (00) - Fixed, always reads 0x00
B04 (00) - Fixed, always reads 0x00
B05 (85) - Not entirely random: pairs of consecutive frames alternate between having consecutive values and not having.
B06 (00) - Contains the following flags:
                b000000x0 - pedal assist (P05 setting: x = 1 -> on; x = 0 -> off)
                b00000x00 - cruise control (P06 setting: x = 1 -> on; x = 0 -> off)
                b0000x000 - soft start (P07 setting: x = 1 -> on; x = 0 -> off)
B07 (46) - Fixed (P08 setting -> 0x46 = 70%)
B08 (00) - Fixed, always reads 0x00
B09 (80) - Fixed, always reads 0x80
B10 (02) - EABS (P09 setting: 0x00 to 0x02)
B11 (00) - Fixed, always reads 0x00
B12 (00) - Fixed, always reads 0x00
B13 (00) - Fixed, always reads 0x00
B14 (43) - checksum (XOR of bytes B0 to B13)
```

**Note:**

Apparently the P-settings P00 to P04 are only used internally by the LCD for calculations 
and actions done on its side (e.g. to determine the speed and present in the correct
units).

Regarding the gears it is still unknown how (and if) these are communicated to the speed 
controller, as this data is not obviously visible in the frames sent by the LCD. There could 
be a different type of frame being sent whenever the speed limit is reached, but this is yet 
to be tested and observed.

2. ESC to LCD:

Example:

```
36 19 00 5b 7e 5b 00 5b 5b 5b 65 6e e3 5b b9
```

Structure:

```
B00 (36) - Fixed
B01 (19) - Sequence (00, 01, 02, ..., FF)
B02 (00) - Fixed (padding apparently)
B03 (5b) - Entropy value (probably adopted as an extra measure to avoid framing errors). 
           The values in B04, B05 and B07 to B13 must be subtracted from this value to 
           obtain the payload. When value smaller than B03, add 0xFF.
B04 (7e) - Subtract B03. Brakes and turbo mode flags: 0x20 - brakes on; 0x03 - turbo; 0x23 - brakes + turbo
B05 (5b) - Subtract B03. Always reads 0x00
B06 (00) - Fixed (padding apparently)
B07 (5b) - Subtract B03. Proportional to wheel speed, most significant byte. 
B08 (5b) - Subtract B03. Proportional to wheel speed, least significant byte.
B09 (5b) - Subtract B03. Power/motor current most significant byte (?).
B10 (65) - Subtract B03. Power/motor current least significant byte (?). Minimum value 0x0a when throttle pressed.
B11 (6e) - Subtract B03. Usually reads 0x13. Battery voltage? Temperature?
B12 (e3) - Subtract B03. Usually reads 0x87 or 0x88. Battery voltage? Temperature?
B13 (5b) - Subtract B03. Always reads 0x00
B14 (b9) - checksum (XOR of bytes B0 to B13)
```


## References


 * QS-S4 similar protocol: https://endless-sphere.com/forums/viewtopic.php?t=111236
