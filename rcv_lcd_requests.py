import argparse
import sys
import binascii
import serial
import datetime

FRAME_SIZE = 15
PAYLOAD_SIZE = 9
BAUD_RATE = 1200
READ_TIMEOUT = 30
WHEEL_PERIMETER = 0.8777

FLAG_PAS = 1
FLAG_CRUISE_CTL = 2
FLAG_SOFT_START = 3

parser = argparse.ArgumentParser(description='Listens to the requests sent by the e-Scooter JP LCD display via UART.')

parser.add_argument('serial_port', type=str,
                    help='the serial device for the communication')

args = parser.parse_args()

# Frame fields:

raw_frame = bytearray(FRAME_SIZE)
frame_seq = 0
entropy_key = 0
power_setting = 0
config_flags = 0
eabs = 0
checksum = 0
checksum_calc = 0

# state variables:

frame_byte = 0
payload_byte = 0
is_beginning = True
valid_frame = True
last_frame = datetime.datetime.now()

def decode_short(short_bytes):
    return int.from_bytes(short_bytes, byteorder='big')

def decode_flag(byte_val, position):
    return byte_val >> position & b'\x01'[0]

with serial.Serial(args.serial_port, BAUD_RATE, timeout=READ_TIMEOUT) as ser:
    while (byte := ser.read(1)):
        raw_frame[frame_byte] = byte[0]

        # 0x01 0x03 should be the beginning of a regular frame:

        if frame_byte == 0:
            if byte != b'\x01':
                print(f'Unexpected first byte: {byte}')
                valid_frame = False
        elif frame_byte == 1:
            if byte != b'\x03':
                print(f'Unexpected 2nd byte: {byte}')
                valid_frame = False                
        elif frame_byte == 2:
            # this is the frame sequence field
            frame_seq = byte[0]
            print(f'Got frame nr: {frame_seq}')
            if is_beginning and frame_seq != 2:
                print(f'Got unexpected sequence in first frame: {frame_seq}')
                valid_frame = False
            else:
                is_beginning = False
        #elif frame_byte == 3 or frame_byte == 4:
        #   print(f'Got the padding byte nr {frame_byte}.')
        elif frame_byte == 5:
            # entropy byte:
            entropy_key = byte[0]
        #elif frame_byte == 6:
        #    print(f'Got the padding byte nr {frame_byte}.')
        elif frame_byte == 7:
            power_setting = byte[0]
        #elif frame_byte == 8:
        #    print(f'Got the padding byte nr {frame_byte}.')
        elif frame_byte == 9:
            config_flags = byte[0]
        elif frame_byte == 10:
            eabs = byte[0]
        #elif frame_byte >= 11 or frame_byte <  14:
        #    print(f'Got the padding byte nr {frame_byte}.')            
        elif frame_byte == 14:
            # checksum:
            checksum = byte[0]

        if frame_byte < 14 and valid_frame:
            checksum_calc = checksum_calc ^ byte[0]
            frame_byte += 1
        else:            
            curr_frame = datetime.datetime.now()
            delta_time = curr_frame - last_frame
            last_frame = curr_frame

            # print the raw frame:
            print('Raw frame:  ' + binascii.hexlify(raw_frame, ' ').decode("utf-8"))

            # let's decode and print the data:
            if checksum_calc == 0 or checksum != checksum_calc:
                print("Checksums don't match:")
                print(f'Parsed checksum: {checksum}')
                print(f'Calculated checksum: {checksum_calc}')
            else:
                pas = decode_flag(raw_frame[6], FLAG_PAS)
                cruise_ctl = decode_flag(raw_frame[6], FLAG_CRUISE_CTL)
                soft_start = decode_flag(raw_frame[6], FLAG_SOFT_START)
                print(f'Time lapse: {delta_time}; PAS: {pas}; Cruise Ctl: {cruise_ctl}; Soft start: {soft_start}; Power limit: {raw_frame[7]}; EABS: {raw_frame[10]}')
            frame_byte = 0
            checksum_calc = 0
            valid_frame = True
