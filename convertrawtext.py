# formattext.py
import tkinter as tk
from tkinter import Canvas, ttk, filedialog, Text, Frame
from tkinter import messagebox
#from tkinterhtml import HtmlFrame
from tkhtmlview import HTMLScrolledText
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
#from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm,cm
from reportlab.graphics.shapes import Circle, Rect, Line
from reportlab.graphics import renderPDF
from reportlab.lib.colors import white,black,red
from pdfviewer import ShowPdf
import os
import re
import html
from settings import get,set, getF, getI
import ast
from collections import Counter
from reportlab.pdfgen import canvas
from PIL import Image, ImageEnhance, ImageFilter, ImageDraw
from io import BytesIO
from reportlab.lib.utils import ImageReader
import math
from reportlab.pdfbase import pdfmetrics
    #import reportlab.lib.fonts
from tkinter import filedialog, messagebox
import atexit
import tempfile
from time import time

background_image = None

chord_overrides={} #abusing a global for this data.


#temp file
temp_file='tmppdf.pdf'

temp_file=tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)

print ("Temp file:", temp_file.name)

#BPM:
first_press_time = 0.0
last_press_time = 0.0
click_count = 0


def del_tmp_file():
    if os.path.exists(temp_file.name):
        os.remove(temp_file.name)

atexit.register(del_tmp_file)


def seems_like_a_chord(chord):
    # The first character is A-G (uppercase).
    # The subsequent characters can be 1,2,3,4,5,6,7,9, /, +, -, b, #, M, m, a, j, s, u, o, d, i or blank.
    pattern = r'^[A-Ga-g][b#]?[1-7,9/#bMmajsuo\+di-]*$'
    return bool(re.match(pattern, chord))


def map_chord(chord, frets, strings):
    global chord_overrides

    # Define the regex pattern for a valid chord
    # The subsequent characters can be 1,2,3,4,5,6,7,9, /, +, -, b, #, M, m, a, j, s, u, o, d, i or blank.
    chord_pattern = re.compile(r'^[A-Ga-g][b#]?[1-7,9/#bMmajsuo\+di-]*$')

    # Check if the chord is valid and if the frets and strings inputs are valid
    if chord_pattern.fullmatch(chord) and re.fullmatch(r'[0-9A-Fa-fx]*', frets) and len(frets) == strings:
        chord_overrides[chord] = frets
        return True
    return False




def int_to_roman(input):
    """ Convert an integer to a Roman numeral. """
    
    if not isinstance(input, int) or input <= 0 or input >= 4000:
        return str(input)

    ints = (1000, 900,  500, 400, 100,  90, 50,  40, 10,  9,   5,  4,   1)
    nums = ('M',  'CM', 'D', 'CD','C', 'XC','L','XL','X','IX','V','IV','I')
    result = []
    for i in range(len(ints)):
        count = int(input / ints[i])
        result.append(nums[i] * count)
        input -= ints[i] * count
    return ''.join(result)

def roman_to_int(input):
    """ only for smaller roman numbers. accepts integers too. """
    if str(input).isdigit():
        return int(input)

    roman_numerals = {'I': 1, 'IV': 4, 'IX': 9, 'V': 5, 'X': 10}
    numerals = re.findall('IV|IX|I|V|X', input)
    return sum(roman_numerals[numeral] for numeral in numerals)


def draw_fretboard(canvas, x, y, fret_positions, blue_fret_positions, chord_name="", capo=0):
    string_spacing = 2 * mm
    fret_spacing = 3 * mm
    circle_radius = 0.75 * mm
    circle_radius2 = 0.50 * mm
    try:
        frets = max(fret for fret in fret_positions if isinstance(fret, int))
    except:
        frets=0

    strings = len(fret_positions)
    fret_length = (strings-1) * string_spacing


    canvas.setStrokeColorRGB (*[0.0,0.0,0.0])

    # Draw the chord name
    canvas.setFont("Helvetica", 10)
    canvas.drawString(x, y+5 , chord_name)

    # Handle barre chords
    barre_fret = 0
    if all(isinstance(fret, int) and fret > 0 for fret in fret_positions):
        barre_fret = min(fret for fret in fret_positions if isinstance(fret, int))
        if (barre_fret>3):
            fret_positions = ['x' if fret == 'x' else fret - barre_fret for fret in fret_positions]
            frets -= barre_fret - 1
        if (barre_fret):
            canvas.setFont("Times-Bold", 12)
            canvas.drawString(x+fret_length+2, y-fret_spacing*(0.3 if barre_fret>=3 else barre_fret) , f" {int_to_roman(barre_fret+capo)}")


    frets = max(fret for fret in fret_positions if isinstance(fret, int))
    frets = frets - barre_fret
    if frets<3:
        frets=3


    canvas.setFont("Helvetica", 10)

    # Draw the frets
    for i in range(frets+2):  # +2 to get correct number of frets and account for barre
        canvas.setLineWidth(2 if i==0 else 1)
        fret_y = y - i * fret_spacing
        
        canvas.line(x, fret_y, x + fret_length, fret_y)

    for i in range(strings):
        string_x = x + i * string_spacing

        # Draw the string
        canvas.line(string_x, y, string_x, y - (frets + 1) * fret_spacing)

    for i in range(strings):
        string_x = x + i * string_spacing

        # Draw the fret position
        fret = fret_positions[i]
        if isinstance(fret, int):
            if fret > 0:  # fretted note
                fret_y = y - (fret - 1) * fret_spacing - fret_spacing/2  # adjust to draw in the middle of the fret
                canvas.setFillColorRGB(0,0,0)
                canvas.circle(string_x, fret_y, circle_radius, fill=1)
            elif fret == 0:  # open string
                canvas.setStrokeColorRGB(1,1,1)
                canvas.setFillColorRGB(1,1,1)
                canvas.circle(string_x, y, circle_radius2, fill=1)
                canvas.setStrokeColorRGB(0,0,0)
                canvas.setFillColorRGB(0,0,0)
                canvas.circle(string_x, y, circle_radius2, fill=0 if barre_fret == 0 else 1)
        elif fret == 'x':  # muted string
            canvas.setStrokeColorRGB(0,0,0)
            canvas.line(string_x-3,y-3,string_x+3,y+3)
            canvas.line(string_x+3,y-3,string_x-3,y+3)

    for stringidx, fret in blue_fret_positions:
        string_x = x + stringidx * string_spacing
        fret_y = y - (fret - 1) * fret_spacing - fret_spacing/2  # adjust to draw in the middle of the fret
        canvas.setFillColorRGB(0,0,1)
        canvas.circle(string_x, fret_y, circle_radius*0.625, fill=1)
        canvas.setFillColorRGB(0,0,0)


def draw_keyboard_and_notes(c, x_start, y_start, notes, chord_name, octaves=1):
    # Set up constants
    KEY_WIDTH = 2.5  # mm
    KEY_HEIGHT = 7  # mm
    DOTWH=5.5
    DOTBH=2.2
    BLACK_KEY_WIDTH = KEY_WIDTH * 2 / 3  # mm
    BLACK_KEY_HEIGHT = KEY_HEIGHT * 0.6  # mm
    NUM_KEYS = 12  # number of keys in an octave

    # Define the keys
    white_keys = [0, 2, 4, 5, 7, 9, 11]  # C, D, E, F, G, A, B
    black_keys = [1, 3, 6, 8, 10]  # C#, D#, F#, G#, A#
    blackposindex=[1, 3, -1, 6, 8, 10]

    # Calculate total keys to be drawn considering octaves as float
    total_white_keys = math.ceil(octaves * 8)  # 7 white keys in an octave

    # Draw the chord name
    c.setFont("Helvetica", 10)
    c.drawString(x_start, y_start+5 , chord_name)


    # Draw the keyboard
    for key in range(total_white_keys):
        x = x_start + key * KEY_WIDTH * mm
        key_num = key % 7  # There are 7 white keys in an octave

        c.setFillColor(white)
        c.rect(x, y_start, KEY_WIDTH * mm, -KEY_HEIGHT * mm, fill=True, stroke=True)


    for key in range(total_white_keys):
        x = x_start + key * KEY_WIDTH * mm
        key_num = key % 7  # There are 7 white keys in an octave
        # Draw the black keys
        if key_num in [0, 1, 3, 4, 5]:  # The black keys are between these white keys
            c.setFillColor(black)
            c.rect(x + KEY_WIDTH * mm *0.65, y_start, BLACK_KEY_WIDTH * mm if key<total_white_keys-1 else 0.5*BLACK_KEY_WIDTH*mm, -BLACK_KEY_HEIGHT * mm, fill=True, stroke=False)



    rootoffset=0
    rootd=0

    # Draw the notes    
    lastnote=None
    for note in notes:        
        key = note % 12
        #find index of key in list white or black keys:
        offset=0
        if key in white_keys:
            offset=white_keys.index(key)
        if key in black_keys:
            offset=blackposindex.index(key)+0.5
                    
        if lastnote is not None and (key<lastnote):
            key+=12
            offset+=7

        if offset>=(total_white_keys-0.5):
            key=key%12
            offset=offset%7

        lastnote=key

            
        x = x_start + offset * KEY_WIDTH * mm

        d=0
        if key%12 in white_keys:
            c.setFillColor(black)
            c.setStrokeColor(black)
            d=DOTWH

        elif key%12 in black_keys:
            c.setFillColor(white)
            c.setStrokeColor(white)
            d=DOTBH

        if note==notes[0]:
            rootoffset=offset
            rootd=d


        # Paint the root note bigger and dark red
        if note == notes[0]:
            c.setFillColor(red)
            c.circle(x + KEY_WIDTH * mm / 2, y_start - d*mm , KEY_WIDTH * mm / 3, fill=True)
        else:
            c.circle(x + KEY_WIDTH * mm / 2, y_start - d*mm , KEY_WIDTH * mm / 4, fill=True)

    #when all is done, make sure the root note was not overriden by another circle:
    c.setFillColor(red)
    c.circle(x_start + rootoffset * KEY_WIDTH * mm + KEY_WIDTH * mm / 2, y_start-rootd * mm , KEY_WIDTH * mm / 3, fill=True)
    c.setFillColor(black)
    c.setStrokeColor(black)
         

def adjust_tuning_for_capo(tuning, capo):
    #return tuning
    notes = {
        'C': 0, 'C#': 1, 'Db': 1, 'D': 2, 'D#': 3, 'Eb': 3, 'E': 4, 'E#': 5, 'Fb': 4, 'F': 5,
        'F#': 6, 'Gb': 6, 'G': 7, 'G#': 8, 'Ab': 8, 'A': 9, 'A#': 10, 'Bb': 10, 'B': 11, 'B#': 0, 'Cb':11,
    }
    note_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
   
    #reverse_notes = {v: k for k, v in notes.items()}  # To retrieve note names from numbers
    adjusted_tuning = []

    for note in re.findall('([A-G](#|b)?)', tuning):
        if note[0] in notes:
            adjusted_note_index = (notes[note[0]] + capo) % 12
            # Get the first matching note name from reverse_notes
            #adjusted_note_name = next(name for name, index in reverse_notes.items() if index == adjusted_note_index)
            adjusted_note_name=note_names[adjusted_note_index]
            adjusted_tuning.append(adjusted_note_name)
        else:
            adjusted_tuning.append(note[0])

    return adjusted_tuning



def chord_to_fret(chord, tuning='EADGBE', capo=0):
    #if tuning=='EADGBE':
    #    #ok, a few hardcoded ones.
    #    if (chord=="D7b5"):
    #        return ['x','x',0,1,1,2]
    #    if (chord=="Em7b5"):
    #        return [0,1,0,3,3,3] #alternate xx2333?

    if chord in chord_overrides.keys():
        frets=chord_overrides[chord]
        return [int(f) if f.isdigit() else f for f in frets], []
    

    tuninglist=adjust_tuning_for_capo(tuning, capo)
    try:
        _,fret_positions, blue_fret_positions = tones_to_guitar(chord_to_tones(chord), tuninglist, 0, capo)  # convert chord to fret positions
        return fret_positions, blue_fret_positions
    except:
        return #[0,0,0,0,0,0], [0,0,0,0,0,0]

def draw_all_chords(canvas, chordsfound, margin_left, margin_top, tuning, capo):
    x = margin_left
    y = margin_top
    
    if int(get("Options", "PrintGuitarChords", 1)):
        if capo>0:
            canvas.setFont("Times-Bold", 14)
            canvas.drawString(x, y+16, f"CAPO: {int_to_roman(capo)}")
        
        for chord, tones in chordsfound.items():
            fret_positions, blue_fret_positions = chord_to_fret(chord, tuning, capo)  # convert chord to fret positions
            if x > 500:  # if the x coordinate exceeds 500
                x = margin_left  # start at the left margin again
                y -= 2 * cm  # move down to the next line
            draw_fretboard(canvas, x, y, fret_positions, blue_fret_positions, chord, capo)  # draw the chord
            x += 2 * cm  # move to the right for the next chord

        global chord_overrides
        for chord, tones in chord_overrides.items():
            fret_positions, blue_fret_positions = chord_to_fret(chord, tuning, capo)  # convert chord to fret positions
            if x > 500:  # if the x coordinate exceeds 500
                x = margin_left  # start at the left margin again
                y -= 2 * cm  # move down to the next line
            draw_fretboard(canvas, x, y, fret_positions, blue_fret_positions, chord, capo)  # draw the chord
            x += 2 * cm  # move to the right for the next chord


    if int(get("Options", "PrintPianoChords", 1)):
        x = margin_left #we do not per se have to do that here. could save space and omit the new line:
        y -= 2.5 * cm
        for chord, tones in chordsfound.items():
            if x > 500:  # if the x coordinate exceeds 500
                x = margin_left  # start at the left margin again
                y -= 1.75 * cm  # move down to the next line
            draw_keyboard_and_notes (canvas, x, y, tones, chord, 1)  # draw the chord
            x += 2.5 * cm  # move to the right for the next chord

def process_image(width, height, opacity, filename):
    # Open image with PIL and resize it
    img = Image.open(filename)
    img = img.resize((width, height))

    # Create a new white image with the same size
    white_img = Image.new('RGB', img.size, (255, 255, 255))

    #Blend edges to white
    mask = Image.new("L", img.size, 0)
    border_width = min(width, height) // 20  # Change this to your preference
    for i in range(border_width):
        ImageDraw.Draw(mask).rectangle(
            [i, i, mask.size[0] - i, mask.size[1] - i],
            outline=255,
            fill=255
        )
    #mask = Image.new("L", img.size, 255)
    #mask_width = min(width, height) // 10  # Change this to your preference
    #mask_rect = (
    #    mask.size[0] // 2 - mask_width // 2,
    #    mask.size[1] // 2 - mask_width // 2,
    #    mask.size[0] // 2 + mask_width // 2,
    #    mask.size[1] // 2 + mask_width // 2
    #)

    mask = mask.filter(ImageFilter.GaussianBlur(border_width / 2))
    #img = Image.composite(img, white_img, mask)

    ## Apply transparency
    #img = img.convert("RGBA")
    #for i in range(img.width):
    #    for j in range(img.height):
    #        r, g, b, a = img.getpixel((i, j))
    #        img.putpixel((i, j), (r, g, b, int(a * opacity)))

    # Apply transparency
    img = img.convert("RGBA")
    data = img.getdata()
    new_data = []
    for item in data:
        r, g, b, a = item
        new_data.append((r, g, b, int(a * opacity)))
    img.putdata(new_data)


    # Save the image in a BytesIO object
    img_byte_arr = BytesIO()
    img.save(img_byte_arr, format='PNG')
    img_byte_arr = img_byte_arr.getvalue()

    return img_byte_arr

def make_background_image():
    #x,y=get("Background","Position", "250x100").split('x')
    try:

        w,h=map(int, get("Background","Size", "200x100").split("x"))
        opacity=int(get("Background","Opacity", "50"))
        imagefile=get("Background", "Image", "")
        if imagefile=="" or not os.path.exists(imagefile):
            return None
        global background_image
        background_image=process_image(w,h,0.01*opacity, imagefile)
        return background_image
    except ValueError:
        print ("Error making image, maybe invalid setting data.")



def draw_transparent_image(c, x, y, width, height, img_byte_arr):
    # Draw the image on the canvas using the reportlab library
    img = Image.open(BytesIO(img_byte_arr))
    c.drawImage(img, x, y, width, height)

def draw_background_image(c):
    if background_image==None:
        return
    if not int(get("Background", "Show", 1)):
        return
    x,y=map(int, get("Background","Position", "250x100").split('x'))
    w,h=map(int, get("Background","Size", "200x100").split('x'))

    # Draw the image on the canvas using the reportlab library
    #img = Image.open(BytesIO(background_image))
    # Create an ImageReader from the BytesIO object
    #c.drawImage(img, x, y, w, h)
    img = Image.open(BytesIO(background_image)) #, width=w, height=h)
    #img.save ("tmpbgimg.png")
    image_reader = ImageReader(img)
    # Draw the image on the canvas
    c.drawImage(image_reader, x, y, w, h)

def draw_image_from_file(c, filename, x, y, width, height):
    try:
        img = Image.open(filename)
        if width==0:
            width=img.width
        if height==0:
            width=img.height
        reader=ImageReader(img)
        #c.setBlendMode(canvas.blendmode.MULTIPLY)
        c.drawImage(reader, x, y, width, height,mask=[250,255,250,255,250,255])
        #c.setBlendMode(canvas.blendmode.NORMAL)
    except:
        pass




def transpose_chords(chords, transpose_value):
    notes = {
        'C': 0, 'C#': 1, 'Db': 1, 'D': 2, 'D#': 3, 'Eb': 3, 'E': 4, 'F': 5,
        'F#': 6, 'Gb': 6, 'G': 7, 'G#': 8, 'Ab': 8, 'A': 9, 'A#': 10, 'Bb': 10, 'B': 11
    }
    note_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
   
    transposed_chords = []

    for chord in chords:
        match = re.match(r'([A-G][b#]?)(.*)', chord)
        if match:
            root = match.group(1)
            if root in notes:
                transposed_note_index = (notes[root] + transpose_value) % 12
                transposed_root = note_names[transposed_note_index]
                transposed_chord = transposed_root + match.group(2)
                transposed_chords.append(transposed_chord)
        else:
            transposed_chords.append(chord)

    return transposed_chords



def open_image_dialog():
    # Open the file dialog and get the selected filename
    filename = filedialog.askopenfilename(filetypes=(("Image files", "*.png;*.jpg;*.jpeg;*.bmp;*.tif;*.gif"), ("All files", "*.*")))

    # Check if a file was selected
    if filename:
        try:
            # Try to open the file with PIL to check if it's a valid image file
            Image.open(filename)
            make_background_image()
            return filename
        except IOError:
            messagebox.showwarning("Invalid image file", "The selected file is not a valid image file.")





def select_image():
    background = open_image_dialog()
    set("Background", "Image", background)
    get("Background", "Position", "250x20")
    get("Background", "Size", "200x100")
    set("Background", "Show", "1")




def tones_to_guitar(tones, tuning=['E', 'A', 'D', 'G', 'B', 'E'], barre=0, capo=0):
    # we ignore capo for now, as we have adjusted the tuning already. we just assume it has no impact on further fingering.
    # Define a dictionary to map note names to their numeric values
    note_values = {'C': 0, 'C#': 1, 'Db': 1, 'D': 2, 'D#': 3, 'Eb': 3, 'E': 4, 'F': 5, 'F#': 6, 'Gb': 6, 'G': 7, 'G#': 8, 'Ab': 8, 'A': 9, 'A#': 10, 'Bb': 10, 'B': 11}
    if len(tones)==0:
        return "xxxxxx", [0,0,0,0,0,0]
    # Initialize a list to hold the fret positions for each string
    fret_positions = []
    used_tones = []

    bass_tone = tones[0] % 12
    # If the first tone is a bass tone only, pop it from the list
    if tones[0] >= 12 and len(tones)>1:
        tones.pop(0)

    # Loop through each string and find the lowest fret position that produces the current tone on this string
    for i, string in enumerate(tuning):
        # Find the lowest fret position that produces the current tone on this string
        min_fret = 15
        for fret in range(12):
            tone = (note_values[string] + fret) % 12
            if tone in tones and (min_fret is None or fret < min_fret) and (fret>=barre):
                if i < 2 and (tone not in tones[:3]): #skip modifiers on base strings:
                    continue
                min_fret = fret
                if tone not in used_tones:  # add the tone to the used tones list
                    used_tones.append(tone)

        # Add the fret position to the list
        fret_positions.append(min_fret)

    #for tone in tones:
    #    if tone not in used_tones:
    #        optimal_fret = None
    #        optimal_string = None
    #        for fret in range(barre, 12):
    #            for i in range(3, 6):  # loop over the higher strings
    #                if (note_values[tuning[i]] + fret) % 12 == tone:
    #                    if optimal_fret is None or fret < optimal_fret:  # if this position is lower than the current fret or the string is open
    #                        if fret_positions[i] == 0 or fret_positions[i] > fret:
    #                            optimal_fret = fret
    #                            optimal_string = i
    #        if optimal_fret is not None:
    #            fret_positions[optimal_string] = optimal_fret
    #            used_tones.append(tone)

    # After determining the fret positions for each string
    #root_tone = tones[0]

    # Check if the root note is on one of the first three strings
    root_on_first_three_strings = any((note_values[tuning[i]] + fret_positions[i]) % 12 == bass_tone for i in range(3))

    # If the root note is not on one of the first three strings
    if not root_on_first_three_strings:
        # Initialize variables to store the optimal fret position and string
        optimal_fret = None
        optimal_string = None

        # Iterate over all possible positions of the root note on the first three strings
        for i in range(3):
            for fret in range(24):
                if (note_values[tuning[i]] + fret) % 12 == bass_tone and (fret>=barre):
                    # If this position is lower than the current optimal fret, update the optimal fret and string
                    if optimal_fret is None or fret < optimal_fret:
                        optimal_fret = fret
                        optimal_string = i

        # Set the fret position for the optimal string to the optimal fret
        fret_positions[optimal_string] = optimal_fret


    # Determine if a barre is needed and get its fret position and width
    barre_fret = None
    #barre_width = None

    fingersum=0
    for i in range(len(fret_positions)):
        if fret_positions[i]>barre:
            fingersum+=1
    if fingersum>=5 or (barre>0 and fingersum>=4): 
        barre_fret=barre+1
        

    for i in range(0, len(fret_positions)):
        if fret_positions[i]-barre > 4 and (barre_fret is None or fret_positions[i] < barre_fret):
            barre_fret=barre+1
            #if all(fret_positions[j] >= fret_positions[i] for j in range(i+1)):
            #    barre_fret = fret_positions[i]
                #barre_width = min(6, sum(1 for j in range(i+1) if fret_positions[j] == barre_fret))

    ## Recalculate the fret positions for the strings below the barre
    #for i in range(len(fret_positions)):
    #    if barre_fret is not None and i < barre_width:
    #        fret_positions[i] = max(0, fret_positions[i] - barre_fret)

    # If a barre is needed, recursively call the function with the new barre index
    if barre_fret is not None:
        if barre_fret<12:
            return tones_to_guitar(tones, tuning=tuning, barre=barre_fret)

    # Convert the list of fret positions to a string and insert 'x' for muted strings
    guitar_string = ''
    for i, fret_position in enumerate(fret_positions):
        if fret_position == 0:
            guitar_string += 'o'
        else:
            guitar_string += str(fret_position)
        guitar_string += ' '

    # Initialize a list to hold the blue fret positions
    blue_fret_positions = []

    # Calculate blue fret positions
    for i, string in reversed(list(enumerate(tuning))):
        for fret in range(barre+1, barre+4):
            tone = (note_values[string] + fret) % 12
            if tone in tones:
                # Check if the tone should be blue based on your desired condition
                if tone not in used_tones:  # Replace this with your desired condition
                    blue_fret_positions.append((i, fret))
                    used_tones.append(tone)

    # Return the guitar_string, fret_positions, and blue_fret_positions
    return guitar_string.strip(), fret_positions, blue_fret_positions


def chord_to_tones(chord):
    # Define a dictionary to map notes to their numeric values
    note_values = {'C': 0, 'C#': 1, 'Db': 1, 'D': 2, 'D#': 3, 'Eb': 3, 'E': 4, 'F': 5, 'F#': 6, 'Gb': 6, 'G': 7, 'G#': 8, 'Ab': 8, 'A': 9, 'A#': 10, 'Bb': 10, 'B': 11}

    # Extract bass note if it is present
    bass_note = None
    if '/' in chord:
        chord, bass_note = chord.split('/')
        if bass_note not in note_values:  # if the bass note is invalid, ignore it
            bass_note = None

    # Split the chord into its component parts using regular expressions
    parts = re.findall(r'[A-G][#b]?(?:maj7|M7|maj9|M9|maj11|M11|m9|m7|m6-9|m6|6|13-5|13|11|9|7#5|7b5|7-5|7\+|7sus4|7|dim|aug|sus4|sus2|sus|m)?', chord)

    # Initialize an empty list to hold the tones
    tones = []
    interval_pattern = []

    # Loop through each part and add the tones to the list
    for part in parts:
        # Initialize an empty interval pattern and modifications for each part
        modifications = {}
        interval_pattern = []
        # Determine the root note and the chord type
        if 'b' in part[:2] or '#' in part[:2]:        
            root_note = part[:2]
            chord_type = part[2:]
        else:
            root_note = part[:1]
            chord_type = part[1:]

        # Convert the root note to its numeric value
        root_tone = note_values[root_note]
        tones.append(root_tone)

        # Handle alterations
        if 'b5' in chord_type or '#5' in chord_type:
            if 'b5' in chord_type:
                modifications[7] = 6
            elif '#5' in chord_type:
                modifications[7] = 8
            chord_type = chord_type.replace('b5', '').replace('#5', '')
        if 'b9' in chord_type or '#9' in chord_type:
            if 'b9' in chord_type:
                modifications[14] = 13
            elif '#9' in chord_type:
                modifications[14] = 15
            chord_type = chord_type.replace('b9', '').replace('#9', '')
        if '-5' in chord_type:
            modifications[7] = 6
            chord_type = chord_type.replace('-5', '')


        if chord_type == '':
            interval_pattern.extend([4, 7])
        elif chord_type == 'm':
            interval_pattern.extend([3, 7])
        elif chord_type == '7':
            interval_pattern.extend([4, 7, 10])
        elif chord_type == '7+':
            interval_pattern.extend([4, 8, 10])  # Augmented 7th
        elif chord_type == 'maj7' or chord_type == 'M7':
            interval_pattern.extend([4, 7, 11])
        elif chord_type == '9':
            interval_pattern.extend([4, 7, 10, 14])
        elif chord_type == '6-9':
            interval_pattern.extend([4, 7, 9, 14])  # 6th add 9
        elif chord_type == 'maj9' or chord_type == "M9":
            interval_pattern.extend([4, 7, 11, 14])
        elif chord_type == 'm7':
            interval_pattern.extend([3, 7, 10])
        elif chord_type == 'm9':
            interval_pattern.extend([3, 7, 10, 14])
        elif chord_type == 'dim':
            interval_pattern.extend([3, 6])
        elif chord_type == 'aug':
            interval_pattern.extend([4, 8])
        elif chord_type == 'sus4':
            interval_pattern.extend([5, 7])
        elif chord_type == '7sus4':
            interval_pattern.extend([5, 7, 10])
        elif chord_type == 'sus2' or chord_type == 'sus':
            interval_pattern.extend([2, 7])
        elif chord_type == '6':
            interval_pattern.extend([4, 7, 9])  # 6th chord
        elif chord_type == 'm6':
            interval_pattern.extend([3, 7, 9])  # minor 6th chord
        elif chord_type == '6-9':
            interval_pattern.extend([4, 7, 9, 14])  # 6-9 chord
        elif chord_type == 'm6-9':
            interval_pattern.extend([3, 7, 9, 14])  # minor 6-9 chord
        elif chord_type == '13':
            interval_pattern.extend([4, 7, 10, 14, 17, 21])  # 13th chord
        elif chord_type == '13-5':
            interval_pattern.extend([4, 6, 10, 14, 17, 21])  # 13th chord with flat 5th
        else:
            pass  # silently ignore. raise ValueError(f"Invalid chord type: {chord_type}")



    # Add the interval pattern to the root tone to get the tones for the rest of the chord
    for interval in interval_pattern:
        if interval in modifications:  # check if the interval needs to be modified
            interval = modifications[interval]
        tone = (root_tone + interval) % 12
        tones.append(tone)

    # If a bass note is present, add it to the beginning of the tone list
    if bass_note:
        bass_tone = note_values[bass_note]+12
        tones.insert(0, bass_tone)

    # Return the list of tones
    return tones
 


def chord_to_notes(chord):
    tones=chord_to_tones(chord) #numeric entries, C=0, take as modulo 12 an offset marks special attributes.
    # Convert the pitch numbers to note names
    all_notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    tones = [all_notes[pitch % len(all_notes)] for pitch in tones]
    return tones

def determine_key(chords, weights=[2, 2, 2, 1, 1,1]):
    # Define all notes and enharmonic equivalents
    all_notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    enharmonics = {'C#': 'Db', 'Db': 'C#', 'D#': 'Eb', 'Eb': 'D#', 'F#': 'Gb', 'Gb': 'F#', 'G#': 'Ab', 'Ab': 'G#', 'A#': 'Bb', 'Bb': 'A#'}
    
    # Define major and minor keys and their scales
    major_keys = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    minor_keys = ['Am', 'A#m', 'Bm', 'Cm', 'C#m', 'Dm', 'D#m', 'Em', 'Fm', 'F#m', 'Gm', 'G#m']
    major_scales = {key: [all_notes[(i + all_notes.index(key)) % len(all_notes)] for i in [0, 2, 4, 5, 7, 9, 11]] for key in major_keys}
    minor_scales = {key: [all_notes[(i + all_notes.index(key[:-1])) % len(all_notes)] for i in [0, 2, 3, 5, 7, 8, 10]] for key in minor_keys}
    
    # Initialize a Counter to count the occurrences of each note
    note_counts = Counter()

    # Iterate over each chord, convert to tones, and count the occurrences of each tone
    for chord in chords:
        tones = chord_to_notes(chord)
        note_counts.update(tones)
        #print(f"Chord: {chord}, Tones: {tones}, Note Counts: {note_counts}")


    # Calculate the score for each key based on the frequency of its notes
    key_scores = {}
    for key, scale in {**major_scales, **minor_scales}.items():
        key_scores[key] = sum(note_counts[note] * weights[i % len(weights)] for i, note in enumerate(scale))        
        #print(f"Key: {key}, Scale: {scale}, Score: {key_scores[key]}")

    # Sort the keys by their score, in descending order
    sorted_keys = sorted(key_scores.items(), key=lambda item: item[1], reverse=True)
    
    # The most likely root key is the key with the highest score
    root_key = sorted_keys[0][0] if sorted_keys else 'nokey'
    
    # Use the enharmonic equivalent if it's more appropriate
    #if '#' in root_key and enharmonics[root_key] in ' '.join(chords):
    #    root_key = enharmonics[root_key]
    
    # Return the root key and a list of the keys sorted by their score
    return root_key ,[key for key, _ in sorted_keys], key_scores

def make_key_suggestions(chords):
    root_key, keys_in_order, key_scores = determine_key(chords)
    major_keys = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    circle_of_fifths = ['F', 'Dm', 'C', 'Am', 'G', 'Em', 'D', 'Bm', 'A', 'F#m', 'E', 'C#m', 'B', 'G#m', 'F#', 'D#m', 'C#', 'A#m', 'G#', 'Fm', 'D#', 'Cm', 'A#', 'Gm']


    # Select the top 6 keys
    top_keys = keys_in_order[:6]

    # Initialize the best match score and the likely root key
    best_match_score = -1
    likely_root_key = None
    best_i=None

    # Rotate the circle of fifths and check the alignment at each position
    for i in range(0,len(circle_of_fifths),2):
        rotated_circle = circle_of_fifths[i:] + circle_of_fifths[:i]
        match_score = sum(rotated_circle[j] in top_keys for j in range(6))
        if match_score > best_match_score:
            best_match_score = match_score
            best_i=i
            #likely_root_key = rotated_circle[0]

    # Determine the likely root key based on the best index
    likely_root_major_key = circle_of_fifths[best_i]
    likely_root_minor_key = circle_of_fifths[(best_i+1) % len(circle_of_fifths)]

    # Count the occurrence of major and minor key in the chords list
    major_count = chords.count(likely_root_major_key)
    minor_count = chords.count(likely_root_minor_key)

    # Determine the likely root key based on the count
    likely_root_key = likely_root_major_key if major_count >= minor_count else likely_root_minor_key

    #ok, this mostly seem to work. dont forget it's only a suggestion.

    # Calculate the total score for normalization
    total_score = max(1,sum(key_scores.values()))

    # Normalize the key scores and convert to percentages
    normalized_scores = {key: round((score / total_score) * 100, 2) for key, score in key_scores.items()}
    # Sort the normalized scores in descending order
    sorted_normalized_scores = dict(sorted(normalized_scores.items(), key=lambda item: item[1], reverse=True))
    normalized_scores_string = ', '.join([f'{key}: {score}%' for key, score in list(sorted_normalized_scores.items())[:9]])


    return likely_root_key, normalized_scores_string #f"Possible keys are: {keys_in_order}",

def beautify(c):
    # pretty blunt approach to keep a hint op spacing from the chords lines
    c = c.replace('\t', '        ')  # tabs to spaces
    c = c.rstrip()  # right trim
    c = c.replace('   ', '  ')  # replace triple spaces with double spaces

    while len(c) > 12 and '  ' in c:
        c = c.replace('  ', ' ')  # replace double spaces with single spaces until length is less than 12

    #return c.replace(' ', '&nbsp;')  # replace spaces with non-breaking spaces
    return c #c.replace("b", "♭").replace("#", "\u266F") #\u266D

def format_song_text_as_html(song_text):
    lines = song_text.split('\n')  # split song text into lines
    lines = [line.strip() for line in lines]  # trim all lines
    lines = [line if line else '' for line in lines]  # ensure all blank lines are truly blank

    # remove any remaining double blank lines
    while '\n\n\n' in song_text:
        song_text = song_text.replace('\n\n\n', '\n\n')

    song_text += '\n\n'  # add a blank line at the end

    html_output = '<!DOCTYPE html>\n<html><head></head><body><font size=+2>\n'
    html_output += '<i>&nbsp;&nbsp;&nbsp;' + html.escape(lines[0]) + '</i>\n<table border=0>'

    lleft = []
    right = []
    i = 1

    while i < len(lines):
        if is_chord_line(lines[i]):
            if i < len(lines) - 1 and not is_chord_line(lines[i + 1]):
                lleft.append(beautify(lines[i]))
                right.append(lines[i + 1])
                i += 1
            else:
                lleft.append(beautify(lines[i]))
                right.append(' ')
        else:        
            if (lines[i] == '' and lleft) or (i == len(lines) - 1) or (lleft) or (right):
                lleft.append('')
                right.append('')
                html_output += '<tr><td><font color=#0099AA><i>' + ''.join(html.escape(ll) for ll in lleft)
                #html_output += '<tr><td><i>' + '<br>'.join(html.escape(ll) for ll in lleft)
                html_output += '</i></font></td><td>' + ''.join(html.escape(r) for r in right) + '</td></tr>'
                #html_output += '</i></td><td>' + '<br>'.join(html.escape(r) for r in right) + '</td>'
                lleft = []
                right = []
            else:
                lleft.append(' ')
                right.append(lines[i])
        i += 1

    # add chords
    html_output += '</table><br><br><table>'
    chordsfound.sort()

    #for i, chord in enumerate(chordsfound):
    #    if i % 8 == 0:
    #        html_output += '<tr>'
    #    s = vleChords.get(chord, '')
    #    if s:
    #        html_output += '<td><i>' + html.escape(chord) + '</i><br><font face=monospace size=-1>' + '<br>'.join(html.escape(s[:6])) + '</font></td><td>&nbsp;</td>'

    html_output += '</table></font></body></html>'

    return html_output

def format_song_text_as_pdf(song_text, pdffilename="sfpdfoutput.pdf", preview=True):
    lines = song_text.split('\n')  # split song text into lines
    lines = [line.strip() for line in lines]  # trim all lines
    lines = [line if line else '' for line in lines]  # ensure all blank lines are truly blank

    # remove any remaining double blank lines
    song_text = '\n'.join(lines)
    while '\n\n\n' in song_text:
        song_text = song_text.replace('\n\n\n', '\n\n')
    lines = song_text.split('\n')

    # create a new PDF using ReportLab
    c = canvas.Canvas(pdffilename, pagesize=A4)
    # A4 paper measures 210 x 297 millimeters or 8.27 x 11.69 inches, which is 595 x 842 points in ReportLab's default units.
    # US Letter size is 8.5 x 11 inches (612 x 792 points), and A4 size is 8.27 x 11.69 inches (595 x 842 points). 
    # The intersection of these two sizes is approximately 8.27 x 11 inches (595 x 792 points)
    # One point is 1/72 inch

    # printable area about 54,18 .. 577,824 .. i'd add a bit more left margin really, 72 or 80


    pagetop = 824-getF ("Render", "TopMargin",24)
    marginleft=getI ("Render", "LeftMarginLeft",80)
    maxwidth=595-marginleft-getF ("Render", "RightMargin",36)
    pagebottom=getF ("Render", "BottomMargin",36)

    fontsize=getF ("Render", "FontSize", 13)
    headersize=getF ("Render", "HeaderSize",18)

    spacing=getF ("Render", "LineSpacing",2)

    font = get ("Render", "Font","Helvetica") #('Helvetica', 'Times-Roman')
    fontcursive=get ("Render", "CursiveFont","Helvetica-Oblique") #('Helvetica-Oblique', 'Times-Italic')

    chordwidth = getF ("Render", "ChordsWidth",120) # about 1/4, possibly smaller
    chordfont=fontcursive
    chordfontsize=fontsize-1.5

    # Register a new font for italic text
    #pdfmetrics.registerFont(TTFont('ItalicFont', 'ItalicFontFile.ttf'))  # replace 'ItalicFontFile.ttf' with your italic font file


    tuning = 'EADGBE'
    capo=0
    transpose=0
    global chord_overrides
    chord_overrides={}


    def printHeaders():
        #draw first, so fonts may draw over (white) areas
        if firstpage:
            draw_background_image(c)

        nonlocal y
        y=pagetop
        c.setFont(font, fontsize)

        if (preview):
            #Print some info:
            c.setFont("Helvetica-Oblique", fontsize-3)  # set the font to the italic font for song lines
            c.setFillColorRGB(0.5,0.5,0.5)

            c.drawString(marginleft, pagetop+25, "Suggested Key: "+str(rootkey))
            c.drawString(marginleft, pagetop+12, "Analysis: "+keysuggestions)
            c.setFillColorRGB(0,0,0) 

        if song_title is not None:
            y-=headersize
            c.setFont(font, headersize+2)  # set the font to the italic font for song lines
            c.drawString(marginleft+chordwidth, y, song_title)
        
        if artist is not None:
            y-=headersize
            c.setFont(fontcursive, headersize-2)  # set the font to the italic font for song lines
            c.drawString(marginleft+chordwidth, y, artist)
        
        if other_description_lines is not None:
            c.setFont(fontcursive, fontsize)  # set the font to the italic font for song lines
            tx=c.beginText(marginleft, pagetop-2*fontsize)
            tx.setFont("Courier-Bold", fontsize-1)
            tx.setTextOrigin(marginleft, pagetop-1.2*fontsize)
            #tx.textOut(other_description)
            for desc in other_description_lines:
                tx.textLine(desc)
            c.drawText(tx)
            #c.endText()


    def printFancies():
        #some fancies:
        c.setStrokeColorRGB(*ast.literal_eval(get("Misc","A4MarkerColor", str([0.7, 0.7, 0.5]))))
        c.rect(2, 2, A4[0]-4, A4[1]-4, stroke=1, fill=0)
        c.setStrokeColorRGB(*ast.literal_eval(get("Misc","MarginMarkerColor", str([0.9, 0.9, 0.7]))))
        c.rect(marginleft, pagebottom, maxwidth, pagetop-pagebottom, stroke=1, fill=0)


    def parseParams(line):
        nonlocal marginleft

        # Split the string based on '=' and trim the parts
        parts = [part.strip() for part in line.split('=')] #split command=params
        parts[0] = '---' if parts[0] == '' else parts[0] #if empty (only a = on the line), fill in a dummy command
        parts = [part for part in parts if part] #remove anything empty
        
        # Extract the first parameter
        command = parts[0].lower()
               
        
        # Check if there are multiple parameters
        if len(parts) >= 2: 
            params=[part.strip() for part in parts[1].split(' ')]                    
            param = params[0] #should always exist, right?

            if command == "image":
                #params contains filename without spaces, imagesize in the '10x20' format and position in either '100x200' or '100,200' format.
                #extract the parameters filename, x, y, w, h. Empty parameters result in zero values for those.
                # Extract the filename
                filename = params[0] if len(params) > 0 else ''

                # Extract the image size (w, h)
                w, h = (0, 0)
                if len(params) > 1:
                    try:
                        w, h = map(int, params[1].split('x'))
                    except:
                        w,h=0,0

                # Extract the position (x, y)
                x, yy = (0, 0)
                if len(params) > 2:
                    try:
                        # handle both '100x200' and '100,200' formats
                        if 'x' in params[2]:
                            x, yy = map(int, params[2].split('x'))
                        elif ',' in params[2]:
                            x, yy = map(int, params[2].split(','))
                    except:
                        x,yy=0,0
                            
                if w*h==0: #keep original size
                    w,h=0,0 #todo, extract size now or leave it to image rendering

                if x==0:
                    x=marginleft #yes, so anything 1..marginleft will be printed left of the margin.
                        
                if yy==0: #use the current y position.
                    yy=y #we could adjust for image height, we could also assume one would simply insert blank lines to auto-position.
                    #will see on that. issue is that height may also not be known yet at this point.
                            
                if os.path.exists(filename):
                    draw_image_from_file(c, filename, x, yy, w, h)

            if command == 'halt':
                print("Halt command received.")
            elif command == 'font': #font names are case sensitive, it seems.
                if param in ["Courier","Times-Roman","Helvetica","Times-Italic"] or param in pdfmetrics.getRegisteredFontNames():
                    nonlocal font
                    font = param
            elif command == 'fontcursive':
                nonlocal fontcursive 
                fontcursive = str(param)
            elif command == 'chordfont':
                nonlocal chordfont 
                chordfont = str(param)
            elif command == 'tuning':
                nonlocal tuning
                if len(param)>=3: #we assume 3 bass strings somewhere, and 3 uppers. meanwhile should work for ukelele.
                    tuning = param
            elif command == 'capo':
                nonlocal capo 
                capo = roman_to_int(param)
            elif command == 'transpose':
                nonlocal transpose 
                if (re.match(r'^-?\d+$', param) is not None):
                #if str(param).isnumeric():
                    transpose=int(param)
                else:
                    transpose =  roman_to_int(param) % 12
            elif map_chord(parts[0],param, len(tuning)):
                pass #this function just added it to the global mappings.

            else: #floating point parameters
                try:
                    param = float(param)
                except ValueError:
                    param = get("Default", command, 1.0)
            
                # Process each variable assignment
                if command == 'fontsize':
                    nonlocal fontsize 
                    fontsize = float(param)
                if command == 'chordfontsize':
                    nonlocal chordfontsize 
                    chordfontsize = float(param)
                elif command == 'headersize':
                    nonlocal headersize 
                    headersize = float(param)
                elif command == 'pagetop':
                    nonlocal pagetop 
                    pagetop = float(param)
                elif command == 'marginleft':
                    marginleft = float(param)
                elif command == 'maxwidth':
                    nonlocal maxwidth 
                    maxwidth= float(param)
                elif command == 'spacing':
                    nonlocal spacing 
                    spacing = float(param)
                elif command == 'chordwidth':
                    nonlocal chordwidth
                    chordwidth = float(param)
                else:
                    pass



    # extract headers
    headers=[]
    #iterate over header lines
    line=lines.pop(0)
    while line!='':
        if '=' in line: #parse parameters
            parseParams(line)
        else:
            headers.append(line)
        line=lines.pop(0)




    #replace 'title - artist' by two lines, if needed
    if headers and headers[0] != '':
        parts = [part.strip() for part in headers.pop(0).split('-', 1) if part.strip()]
        headers[:0] = parts[::-1]


    song_title = headers.pop(0) if headers and headers[0] != '' else None
    artist = headers.pop(0) if headers and headers[0] != '' else None
    other_description_lines = []
    while headers and headers[0] != '':
        other_description_lines.append(headers.pop(0))
    #other_description = '\n'.join(other_description_lines) if other_description_lines else None

    # write headers
    y=pagetop
    rootkey=""

    firstpage=True



    #iterate over all lines to sum up chords. use that data to determinate the key. we need to do this first so we can print the key on top of each page.
    allchords=[]
    for line in lines:
        if is_chord_line(line):
            for s in line.split(' '):
                if is_valid_chord(s):
                    allchords.append(s)


    allchords = transpose_chords(allchords, transpose)
    rootkey, keysuggestions = make_key_suggestions(allchords)

    #draw_keyboard_and_notes(c, marginleft, pagetop-100, [0, 2, 4, 5, 7, 9, 11, 12, 14, 16, 17, 19], octaves=1.5)

    printHeaders()
    if (preview):
        printFancies()

    
    # add the song meta data (any lines after the two header lines)
    c.setFont("Helvetica-Oblique", fontsize)  # set the font to the italic font for song lines
    y -= 0.5 * fontsize  # adjust the starting y-coordinate as needed
    for line in headers:
        if line != '':
            c.drawString(marginleft, y, line)
            y -= fontsize  # adjust as needed
        else:
            break #break on first empty line

    c.setFont(font, fontsize)
    
    
    y -= 0.5*fontsize #small gap

    #while i < len(lines):
    #    if ((y<pagebottom) or ((y<pagebottom+4*fontsize) and lines[i]!='')):
    #        c.showPage()
    #        y=pagetop

    #    if is_chord_line(lines[i]):
    #        if i < len(lines) - 1 and not is_chord_line(lines[i + 1]):
    #            lleft.append(beautify(lines[i]))
    #            right.append(lines[i + 1])
    #            i += 1
    #        else:
    #            lleft.append(beautify(lines[i]))
    #            right.append(' ')
    #    else:        
    #        if (lines[i] == '' and lleft) or (i == len(lines) - 1) or (lleft) or (right):
    #            lleft.append('')
    #            right.append('')
    #            c.drawString(marginleft, y, ''.join(ll for ll in lleft))
    #            c.drawString(marginleft+chordwidth, y, ''.join(r for r in right))
    #            y -= fontsize  # move y-coordinate up for the next line
    #            lleft = []
    #            right = []
    #        else:
    #            lleft.append(' ')
    #            right.append(lines[i])
    #    i += 1



    chordsfound={}

    haschord=False
    haslyric=False

    pagebreakflex=getF("Format","PageBreakFlexibleLines", 4)




    #new way, line for line (again)
    for i in range(len(lines)):
        line = lines[i]



        if is_chord_line(line):
            if (haschord or haslyric): #next line
                y-=fontsize+spacing
                haslyric=False
            haschord=True
            #transpose the line
            tline=' '.join(transpose_chords(line.split(), transpose))
            for s in tline.split(' '):
                if is_valid_chord(s):
                    chordsfound[s]=chord_to_tones(s)
                #if s and s not in chordsfound:
                #    chordsfound.append(s)
            c.setFont(chordfont, chordfontsize)
            c.drawString(marginleft, y, beautify(tline))


        else:

            if (line=='' or line=='/P' or line=="/B"): 
                y-=fontsize*1.70
                haslyric,haschord=False,False
            elif line=="/FL":
                #plot a horizonal line
                y-=fontsize/2
                c.setStrokeColor(black)
                c.line(marginleft, y, maxwidth, y)
                y-=fontsize/2
            elif line=="/L":
                #plot a horizonal line
                y-=fontsize/2
                c.setStrokeColor(black)
                c.line(marginleft+chordwidth, y, maxwidth, y)
                y-=fontsize/2
            elif line=="/U": #one line up.
                y+=fontsize             
            elif '=' in line:
                parseParams(line)
    
            else:
                if (haslyric): #new line
                    y-=fontsize+spacing
                c.setFont(font, fontsize)
                c.drawString(marginleft+chordwidth, y, line)
                haslyric=True


        # Check if the next line is a lyric line (and that we're not on the last line)
        next_is_lyric = (i < len(lines) - 1) and not is_chord_line(lines[i + 1])


        if ((y<pagebottom+fontsize) or ((y<pagebottom+pagebreakflex*fontsize) and line!='' and not (haschord and next_is_lyric)) or (line=="/P")):
            firstpage=False
            c.showPage()
            y=pagetop
            printHeaders()
            if (preview):
                printFancies()
            y-=fontsize
            c.setFont(fontcursive, fontsize)
            c.drawString (marginleft+chordwidth, y, "(continued)")
            y-=2*fontsize
            c.setFont(font, fontsize)
            if (line=="/P"):
                continue



    # add chords
    #chordsfound.sort()
    chordsfound=dict(sorted(chordsfound.items()))

    chords=list(chordsfound.keys())

    chords=transpose_chords(chords, transpose)

    ##bit ugly backward compatibility, re-create chordsfound, after transpose
    #chordsfound={}
    #for chord in chords:
    #    chordsfound[chord]=chord_to_tones(chord)


    #for chord in chordsfound:
    #    print (str(chord_to_tones(chord)))
    print (str(chordsfound))

    

    draw_all_chords(c, chordsfound, marginleft, y, tuning, capo)

    #for n,t in chordsfound.items():
    #    print (n, str(t), chord_to_tones(n), tones_to_guitar(chord_to_tones(n)))


    c.save()  # save the PDF    

    return pdffilename



def is_valid_chord(chord: str) -> bool:
    if chord=='Ai' or chord=='ai':
        return False
    pattern = re.compile(r"""
        ^                         # Start of the string
        ([A-Ga-g])                # Root note
        ([b#]*)                   # Optional accidentals (flats or sharps)
        (maj|min|m|dim|°|aug|     # Major, minor, diminished, augmented
        sus[24]?|                 # Suspended
        [mM]?aj?|                 # Major
        [mM]?in?|                 # Minor
        ø|                        # Half-diminished
        [°o]?|                    # Diminished
        (?:maj|M)?[79]?|          # 7th, 9th Major
        m(?:in)?[79]?|            # 7th, 9th Minor
        (?:maj|M)?11|             # 11th Major
        m(?:in)?11|               # 11th Minor
        (?:maj|M)?13|             # 13th Major
        m(?:in)?13|               # 13th Minor
        6|9|                      # 6th, 9th
        \+|                       # Augmented
        7\+|                      # Augmented 7th
        m?7b5|                    # Minor 7th flat 5 and 7th flat 5
        m?6|                      # Minor 6th and Major 6th
        m7-5|                     # Minor 7th with flat 5
        \d*-5|                    # 7-5 or any other digit followed by -5
        )?                        # Chord type is optional (for major triads)
        (-\d+)*                   # Add any digit with a preceding dash 
        (?:/                      # Separator for slash chords (C/A)
            ([A-Ga-g])            # Bass note
            ([b#]*)               # Optional accidentals for bass note
        )?                        # Slash chord notation is optional
        $                         # End of the string
        """, re.VERBOSE)
    return bool(pattern.match(chord))


def seems_like_a_chord(chord):
    # The first character is A-G (uppercase).
    # The subsequent characters can be 1,2,3,4,5,6,7,9, /, +, -, b, #, M, m, a, j, s, u, o, d, i or blank.
    pattern = r'^[A-Ga-g][b#]?[1-7,9/#bMmajsuo\+di-]*$'
    return bool(re.match(pattern, chord))




def is_chord_line(line: str) -> bool:
    # Skip empty lines
    if not line:
        return False
    global chord_overrides

    words = line.split()
    chords = [word for word in words if is_valid_chord(word) or word in chord_overrides.keys()]
    non_chords = [word for word in words if not word in chords]

    # Return true if more than 65% of words are chords and there are more than 3 words
    is_chord_line = len(chords) / len(words) > 0.65 

    # If there are at least 2 recognized chords, print any unrecognized chords
    if len(chords) >= 2 and non_chords:
        print(f"Unrecognized chords in line: {', '.join(non_chords)}")

    return is_chord_line

class FormatText(Frame):
    def __init__(self, parent, on_next):
        super().__init__(parent)
        self.on_next = on_next
        
        self.create_widgets()

        self.file_path=None

        make_background_image()

    def show_context_menu(self, event):
        self.context_menu.post(event.x_root, event.y_root)


    def select_all_text():
        raw_text.tag_add("sel", "1.0", "end")

    def create_widgets(self):
        paned_window = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        paned_window.pack(expand=True, fill=tk.BOTH)

        # Left pane
        left_pane = Frame(self, width=300)
        left_pane.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)
        paned_window.add(left_pane)

        # Middle pane
        self.middle_pane = Frame(self, width=200)
        self.middle_pane.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)
        paned_window.add(self.middle_pane)

        # Right pane
        #right_pane = Frame(self, width=200)
        #right_pane.pack(side=tk.RIGHT, expand=True, fill=tk.BOTH)
        #paned_window.add(right_pane)


        self.raw_text = Text(left_pane, wrap=tk.WORD, width=60)
        self.raw_text.pack(expand=True, fill=tk.BOTH)
        self.raw_text.insert('1.0', "A\nB\nC\nInput Text\n\nA B C\nTest")


        #context menu
        self.context_menu = tk.Menu(self.raw_text, tearoff=0)
        self.context_menu.add_command(label="Cut", command=lambda: self.raw_text.event_generate("<<Cut>>",))
        self.context_menu.add_command(label="Copy", command=lambda: self.raw_text.event_generate("<<Copy>>"))
        self.context_menu.add_command(label="Paste", command=lambda: self.raw_text.event_generate("<<Paste>>"))
        self.context_menu.add_command(label="Select All", command=lambda: self.raw_text.tag_add("sel", "1.0", "end"))
        self.context_menu.add_command(label="Save File", command=self.save_as_file)

        self.raw_text.bind("<Button-3>", self.show_context_menu)

        load_button = ttk.Button(left_pane, text="Load Text File", command=self.load_file)
        load_button.pack(side=tk.LEFT, pady=10)

        load_image_button = tk.Button(left_pane, text="Select image", command=select_image)
        load_image_button.pack(side=tk.LEFT, pady=10)


        save_button = ttk.Button(left_pane, text="Save Text File", command=self.save_file)
        save_button.pack(side=tk.LEFT, pady=10)

        save_as_button = ttk.Button(left_pane, text="Save Text As...", command=self.save_as_file)
        save_as_button.pack(side=tk.LEFT, pady=10)

        convert_button = ttk.Button(left_pane, text="Convert", command=self.convert_text)
        convert_button.pack(side=tk.LEFT, pady=10)


        #self.converted_text = HTMLScrolledText(right_pane, html="<h1>Loading...</h1>")
        #self.converted_text.pack(expand=True, fill=tk.BOTH)

        #next_button = ttk.Button(left_pane, text="Next", command=self.next_module)
        #next_button.pack(pady=10)

        savepdf_button = ttk.Button(left_pane, text="Save PDF File", command=self.save_pdf_file)
        savepdf_button.pack(side=tk.LEFT, pady=10)



        #BPM:

        def bpm_button_pressed():
            global click_count, first_press_time, last_press_time
            current_time = time()
            if current_time - last_press_time > 3:
                click_count = 0
            last_press_time=current_time
            if click_count == 0:
                first_press_time = current_time
            click_count += 1
            update_bpm()

        def update_bpm():
            global click_count, first_press_time
            current_time = time()
            
            if click_count <= 1:
                bpm = 100.0
            else:
                time_diff = current_time - first_press_time
                bpm = (click_count - 1) * 60 / time_diff

            bpm_button.config(text="BPM: {:.1f}".format(bpm ))

        bpm_button = tk.Button(
            left_pane,
            text="BPM Button",
            command=bpm_button_pressed,
            #font=("Arial", 16),
            #width=12,
            #height=2
        )
        bpm_button.pack(padx=10, pady=10)


        #self.infopane = self.middle_pane
        #self.infotext = Text(middle_pane, wrap=tk.WORD)
        #self.infotext.pack(expand=True, fill=tk.BOTH)
        #self.infotext.insert('1.0', "Middle test text")

        # Create a Canvas widget to hold the PDF viewer
        #self.pdfcanvas = self.middle_pane #tk.Canvas(self.infopane)
        #self.pdfcanvas.pack(side="left", fill="both", expand=True)

        
        #canvas.create_window((0, 0), window=pdf_view, anchor="nw")
        #self.pdfdisplay=ShowPdf().pdf_view(master=self.middle_pane)
        #self.pdfdisplay=Frame(self, width=200)
        #self.pdfdisplay.pack(expand=True, fill='both')
        #pdfdisplay=pdfrender
        #disp2=disp.pdf_view(self.infopane, pdf_location=r"tmppdf.pdf")

        
        #paned_window.paneconfig(left_pane, minsize=100, width=200)
        #paned_window.paneconfig(right_pane, minsize=100, width=200)

        paned_window.sashpos(0, 300)

        #attach notification to the raw_text
        self.timer_id=None
        self.raw_text.bind("<KeyRelease>", self.text_changed)
        self.raw_text.bind("<<Modified>>", self.text_changed)

        self.raw_text.bind("<<Paste>>", self.on_paste)

        self.load_last_file()

        # Register a callback function to be called when the window is closed
        self.raw_text.winfo_toplevel().protocol("WM_DELETE_WINDOW", self.save_last_file)


    def text_changed(self, event):
        if self.timer_id is not None:
            self.raw_text.after_cancel(self.timer_id)
        self.timer_id = self.raw_text.after(300, self.handle_timer)
        return None

    def on_paste(self, event):
        # Clear the file path when a paste occurs
        self.file_path = None
        

    def handle_timer(self):
        self.timer_id = None
        #self.datachanged()
        self.convert_text()


    def save_last_file(self):
        last = "lastopened.txt"
        with open(last, "w") as file:
            file.write(self.raw_text.get("1.0", "end-1c"))
        self.raw_text.winfo_toplevel().destroy()

    def load_last_file(self):
        #load the last file, if any
        last = "lastopened.txt"
        if (os.path.isfile(last)):
            with open (last, "r") as file:
                self.raw_text.delete(1.0, tk.END)
                self.raw_text.insert (1.0, file.read())

    def load_file(self):
        file_path = filedialog.askopenfilename()
        if file_path:
            with open(file_path, "r") as file:
                self.raw_text.delete(1.0, tk.END)
                self.raw_text.insert(tk.INSERT, file.read())
            self.file_path = file_path

            self.text_changed (self)

    def save_file(self):
        # If the file_path is set (a file was loaded), we use that as the default filename
        default_filename = self.file_path if self.file_path else None

        # If no file was loaded, we extract the filename from the first two lines of text
        if not default_filename:
            first_two_lines = self.raw_text.get(1.0, 'end-1c').split('\n')[:2]
            default_filename = "_".join(first_two_lines) + ".txt"

        # Ask for a filename (if a file was loaded or a filename was extracted, suggest that as default)
        file_path = filedialog.asksaveasfilename(initialfile=default_filename, defaultextension=".txt")

        # If a file_path was returned (the user didn't cancel the dialog)
        if file_path:
            # Check if the file already exists and if so, ask for overwrite confirmation
            if not os.path.exists(file_path) or messagebox.askyesno('Confirmation', 'File exists. Do you want to overwrite?'):
                # If the file doesn't exist, or the user agrees to overwrite, we can write to the file
                with open(file_path, "w") as file:
                    file.write(self.raw_text.get(1.0, tk.END))
                # And update the file_path attribute
                self.file_path = file_path

    def save_as_file(self):
        self.save_file()

    def save_pdf_file(self):
        # If the file_path is set (a file was loaded), we use that as the default filename
        default_filename = None #self.file_path if self.file_path else None

        # If no file was loaded, we extract the filename from the first two lines of text
        if not default_filename:
            first_two_lines = self.raw_text.get(1.0, 'end-1c').split('\n')[:2]
            default_filename = "_".join(first_two_lines) + ".pdf"

        # Ask for a filename (if a file was loaded or a filename was extracted, suggest that as default)
        file_path = filedialog.asksaveasfilename(initialfile=default_filename, defaultextension=".pdf")

        # If a file_path was returned (the user didn't cancel the dialog)
        if file_path:
            # Check if the file already exists and if so, ask for overwrite confirmation
            if not os.path.exists(file_path) or messagebox.askyesno('Confirmation', 'File exists. Do you want to overwrite?'):
                # If the file doesn't exist, or the user agrees to overwrite, we can write to the file
                format_song_text_as_pdf(self.raw_text.get(1.0, tk.END), file_path, False)


    def convert_text(self):
        raw_text = self.raw_text.get(1.0, tk.END)

        format_song_text_as_pdf(raw_text, temp_file.name)

        for w in self.middle_pane.winfo_children():
            w.destroy()

        self.middle_pane.children.clear()

        sp=ShowPdf()
        sp.pdf_view(master=self.middle_pane, pdf_location=temp_file.name)
        




    def convert_text_function(self, raw_text):
        # Implement your text conversion logic here
        #return raw_text.upper()
        return format_song_text_as_html(raw_text)

    def next_module(self):
        self.on_next()
