#!/usr/bin/python
# -*- coding: utf-8 -*

#
# send images to the Wacom Intuos4 OLEDs.
# San Vu Ngoc, 2019
#
# Should be executed with sudo
#

import sys
import stat
import re
import subprocess
import os.path
import argparse
import tempfile

import Image
import struct

DEVICES_PATH = "/sys/bus/hid/devices/"
WACOM_LED = "wacom_led"
STATUS_LED0 = "status_led0_select"
BUTTON = "button%u_rawimg"
DEFAULT_FONT = "LiberationSans-Regular.ttf"
# https://github.com/linuxwacom/input-wacom/wiki/Device-IDs
USB_IDS = [
    ((0x056a, 0x00b9), "PTK-640", "Intuos4", "(6x9)"),
    ((0x056a, 0x00ba), "PTK-840", "Intuos4", "(8x13)"),
    ((0x056a, 0x00bb), "PTK-1240", "Intuos4", "(12x19)"),
    ((0x056a, 0x00bc), "PTK-540WL", "Intuos4", "Wireless")]
TARGET_WIDTH = 64
TARGET_HEIGHT = 32

def check_range (button):
    if button < 0 or button > 7:
        print ("ERROR: button %i out of range."%button)
        return (False)
    else:
        return (True)
    
class Screen:
    """Data for the 8 button images for all 4 led positions"""

    def __init__(self, ids):
        self.ids = ids
        self.raw = [[None for x in range(8)] for led in range(4)]
        
    def get_led (self, led):
        if led is None:
            return (get_led (self.ids))
        else:
            return (led)
        
    def get_raw (self, button, led = None):
        led = self.get_led (led)
        if check_range(button):
            return (self.raw[led][button])
        else:
            return (None)

    def set_raw(self, button, raw_data, led = None):
        led = self.get_led (led)
        if check_range(button):
            self.raw[led][button] = raw_data

    def save(self, filename):
        # we replace None by black images in self.raw
        # TODO really write None...
        true_raw = [[(x if x is not None
                      else bytearray(TARGET_HEIGHT*TARGET_WIDTH/2))
                      for x in led]
                      for led in self.raw]
        with open(filename, 'wb') as outfile:
            outfile.write("(%u,%u)\n"%(self.ids[0], self.ids[1]))
            for led in range(4):
                for button in range(8):
                    outfile.write(true_raw[led][button])

    def load(self, filename):
        size = TARGET_HEIGHT*TARGET_WIDTH/2
        with open(filename, 'rb') as file:
            l = file.readline()
            print (l)
            for led in range(4):
                for button in range(8):
                    self.raw[led][button] = file.read(size)

            
def get_led (ids):
    """Get the status led: 0,1,2,3"""
    path = get_path (ids)
    led_path = os.path.join(path, WACOM_LED, STATUS_LED0)
    with open(led_path, 'r') as f:
        for line in f:
            return (int(line))

def img_to_raw (im, flip=False):
    """Convert an image to a raw 1024 bytearray for the Intuos4.

    Suitable for displaying on one button screen.  'flip' should be True
    if the buttons are on the right-hand side (left-handed configuration).
    """

# cf https://www.kernel.org/doc/Documentation/ABI/testing/sysfs-driver-wacom
# :
# When writing a 1024 byte raw image in Wacom Intuos 4
# interleaving format to the file, the image shows up on Button N
# of the device. The image is a 64x32 pixel 4-bit gray image. The
# 1024 byte binary is split up into 16x 64 byte chunks. Each 64
# byte chunk encodes the image data for two consecutive lines on
# the display. The low nibble of each byte contains the first
# line, and the high nibble contains the second line.
# When the Wacom Intuos 4 is connected over Bluetooth, the
# image has to contain 256 bytes (64x32 px 1 bit colour).
# The format is also scrambled, like in the USB mode, and it can
# be summarized by converting 76543210 into GECA6420.
#                             HGFEDCBA      HFDB7531
        
    #outfile = open(output, "wb")

    width = im.size[0]
    height = im.size[1]
    if width != TARGET_WIDTH or height != TARGET_HEIGHT:
        print ("Warning: we need to resize the %ix%i image to %ix%i"
                   %(width, height, TARGET_WIDTH, TARGET_HEIGHT))
        im = im.resize((TARGET_WIDTH, TARGET_HEIGHT), Image.LANCZOS)
        print (im.size)

    # convert to 8bit grayscale
    im = im.convert(mode="L")

    (w,h) = (TARGET_WIDTH, TARGET_HEIGHT)
    raw = bytearray(w*h/2)
    pos = 0
    
    for j in range(h/2):
        (y, n1, n2) = (h/2 - j, -1, -2) if flip else (j, 0, 1)
        
        for i in range(w):
            low = im.getpixel((i, 2*y + n1)) >> 4  # convert to 4bit grayscale 
            high = im.getpixel((i, 2*y + n2)) >> 4 # (= divide by 16)
            byte = (high << 4) + low
            #outfile.write(chr(byte))
            raw[pos] = byte
            pos += 1

    #outfile.close()
    return (raw)

# not used
def img_to_multi_raw(image, span, flip):
    image = Image.open(filename)
    width = image.size[0]
    height = image.size[1]
    raws = [img_to_raw(image.crop((0,i*height/btn_span, width, (i+1)*height/btn_span)), flip)
                for i in range(span)]
    return (raws)

def ids_from_string (s):
    """Extract (vendor,product) for a line printed by lsusb"""
    s = re.search(r'ID ([0-9A-Fa-f]{4}):([0-9A-Fa-f]{4})\b', s)
    if s is not None:
        vendor = s.group(1)
        product = s.group(2)
        return (int(vendor,16), int(product, 16))
    else:
        print ("ERROR: badly formatted line from lsusb:\n%s"%s)
        return (None)

def wacom_from_id (id):
    return ([wac for wac in USB_IDS if id == wac[0]])
    
def get_usb_ids ():
    """Extract Intuos4 (vendor,product) from lsusb.

    For me it's (0x056A, 0x00B9) = Intuos4 M
    """
    ids = subprocess.check_output(["lsusb"])
    ids = ids.splitlines()
    wacoms = []
    for x in ids:
       w = wacom_from_id (ids_from_string (x))
       if w != []:
           wacoms += w
    if wacoms == []:
        print ("ERROR: No compatible Wacom tablet is connected or recognized.")
        return (None)
    elif len(wacoms) > 1:
        print ("WARNING: several Wacom tablet are connected. We choose the first one")
    w = wacoms[0]
    print ("Using Wacom %s %s (%s)"%(w[2], w[3], w[1]))
    return (w[0])

def split_path (path):
    """Extract (vendor,product) from path.

    example: '0003:056A:00B9.0004' ==> 0x056A, 0x00B9
    """
    l = path.replace(':', '.').split('.')
    return (int(l[1], 16), int(l[2], 16))

def get_path ((vendor, product)):
    """Find corresponding path in DEVICES_PATH.
    """
    l = subprocess.check_output(["ls", DEVICES_PATH])
    l = l.splitlines()
    file = [x for x in l if split_path(x) == (vendor, product)]
    if len(file) == 0:
        print ("ERROR: no corresponding directory found in %s"%DEVICES_PATH)
        return (None)
    else:
        if len(file) > 1:
            print ("Warning: found more than one corresponding directory in %s"%DEVICES_PATH)
        return (os.path.join(DEVICES_PATH, file[0], WACOM_LED))
    

def send_raw (raw, button, usb_ids):

    path = get_path(usb_ids)
    btn_path = os.path.join(path, BUTTON%button)
    os.chmod(btn_path, stat.S_IWOTH)
    outfile = open(btn_path, "wb")
    outfile.write(raw)

def send_image (filename, button, usb_ids, flip = False):

    im = Image.open(filename)
    raw = img_to_raw(im, flip)
    send_raw (raw, button, usb_ids)

def send_multi_image (filename, top_button, btn_span, usb_ids, flip):
    """Send an image that will span vertically over several buttons.

    The image will start at 'top_button'. 'btn_span' is total the number
    of buttons over which the image has to be displayed.
    """
    button = (7 - top_button if flip else top_button)
    if button + btn_span > 8:
        print ("ERROR: there are no %u button(s) available below #%u"%(btn_span, top_button)) 
        return (None)
    image = Image.open(filename)
    width = image.size[0]
    height = image.size[1]
    for i in range(btn_span):
        im = image.crop((0,i*height/btn_span, width, (i+1)*height/btn_span))
        raw = img_to_raw(im, flip)
        button = top_button - i if flip else top_button + i
        send_raw (raw, button, usb_ids)
        # TODO: better to resize first and split next.

def clear_buttons (button, span, usb_ids, flip):
    last_button = (button if span is None else
                       (button + span - 1 if flip else button - span + 1))
    r = range(min(button, last_button), max(button, last_button)+1)
    raw = bytearray(TARGET_HEIGHT*TARGET_WIDTH/2)
    for b in r:
        print ("Clearing button %u"%b)
        send_raw (raw, b, usb_ids)

    
def get_font_path (font):
    l = subprocess.check_output(["fc-list"])
    l = l.splitlines()
    f = [x for x in l if font in x]
    if f == []:
        print ("ERROR: font %s not found"%font)
        return (None)
    return (f[0].split(':')[0])
    
def text_to_img (text, output, font = DEFAULT_FONT, size = None):

    if size is None:
        resize = []
    else:
        resize = ["-pointsize", "%u"%size]
    font_path = get_font_path(font)
    args1 = ["convert",
                 "-size",  "%ux%u"%(TARGET_WIDTH, TARGET_HEIGHT),
                 "-gravity", "Center",
                 "-font", font_path,
                 "-background", "black",
                 "-fill", "white"]
    args2 = ["caption:%s"%text, output]
    ret = subprocess.call(args1 + resize + args2)
    if ret == 0:
        print ("Image %s successfully created"%output)
    else:
        print ("ERROR: in creating %s"%output)
    
def send_text (text, button, usb_ids, flip = False,
                   font = DEFAULT_FONT, size = None):

    _, filename = tempfile.mkstemp(prefix="wacom-", suffix=".png")
    text_to_img(text, filename, font, size)
    im = Image.open(filename)
    raw = img_to_raw(im, flip)
    send_raw (raw, button, usb_ids)
        
#---------------------#
# Command-line Script #
#---------------------#

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--flip", action="store_true",
                        help="Flip images upside-down (for left-handed)")
    parser.add_argument("--clear", action="store_true",
                        help="Clear button")
    parser.add_argument("button", help="button number, between 0 and 7", type=int)
    parser.add_argument("-i", "--image", help="image file")
    parser.add_argument("-t", "--text", help="text message")
    parser.add_argument("-s", "--span", help="if the image has to span over several buttons", type=int)
    args = parser.parse_args()

    ids = get_usb_ids ()
    if ids is None:
        print ("ERROR: Cannot get the Intuos4 ids.")
        exit (1)
    if args.button < 0 or args.button > 7:
        print ("ERROR: Button should be between 0 and 7.")
        exit (1)
    if args.image is None:
        if args.text is None:
            if args.clear is None:
                print ("ERROR: Either an image file, or a text message, or the --clear flag should be provided")
                exit (1)
            else:
                clear_buttons(args.button, args.span, ids, args.flip)                
        else:
            print ("Sending \"%s\" to button %u"%(args.text, args.button))
            send_text(args.text, args.button, ids, args.flip, DEFAULT_FONT, None)
    else:
        if args.text is not None:
            print ("Using image %s and ignoring text %s."%(args.image, args.text))
        if args.span is None:
            send_image(args.image, args.button, ids, args.flip)
        else:
            send_multi_image(args.image, args.button, args.span, ids, args.flip)
    print ("Done")
    
