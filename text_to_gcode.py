#!/usr/bin/python3
# pylint: disable=no-member

from enum import Enum
import os
import math
import argparse


class Instr:
    class Type(Enum):
        move = 0,
        write = 1,

    def __init__(self, *args):
        if len(args) == 1 and type(args[0]) is str:  # args must be a data str
            attributes = args[0].split(' ')
            # G_ X__ Y__
            self.type = Instr.Type.move if attributes[0][1] == '0' else Instr.Type.write
            self.x = float(attributes[1][1:])
            self.y = float(attributes[2][1:])
        elif len(args) == 3 and type(args[0]) is Instr.Type and type(args[1]) is float and type(args[2]) is float:
            self.type, self.x, self.y = args
        else:
            raise TypeError(
                "Instr() takes one (str) or three (Instr.Type, float, float) arguments")

    def __repr__(self):
        return "G%d X%.2f Y%.2f" % (self.type.value[0], self.x, self.y)

    def translated(self, x, y):
        return Instr(self.type, self.x + x, self.y + y)
        
    def scaled(self, scale_factor):
        """Apply scaling to the instruction coordinates"""
        return Instr(self.type, self.x * scale_factor, self.y * scale_factor)


class Letter:
    def __init__(self, *args):
        if len(args) == 1 and type(args[0]) is str:
            self.instructions = []
            for line in args[0].split('\n'):
                if line != "":
                    self.instructions.append(Instr(line))
            pointsOnX = [instr.x for instr in self.instructions]
            self.width = max(pointsOnX) - min(pointsOnX)
        elif len(args) == 2 and type(args[0]) is list and type(args[1]) is float:
            self.instructions = args[0]
            self.width = args[1]
        else:
            raise TypeError(
                "Letter() takes one (str) or two (list, float) arguments")

    def __repr__(self):
        return "\n".join([repr(instr) for instr in self.instructions]) + "\n"

    def translated(self, x, y):
        return Letter([instr.translated(x, y) for instr in self.instructions], self.width)
        
    def scaled(self, scale_factor):
        """Apply scaling to all instructions and width of the letter"""
        scaled_instructions = [instr.scaled(scale_factor) for instr in self.instructions]
        scaled_width = self.width * scale_factor
        return Letter(scaled_instructions, scaled_width)


def readLetters(directory):
    letters = {
        " ": Letter([], 4.0),
        "\n": Letter([], math.inf)
    }
    for root, _, filenames in os.walk(directory):
        for filename in filenames:
            file = open(os.path.join(root, filename), "r")
            letterRepr = file.readline()[1]
            letter = Letter(file.read())
            letters[letterRepr] = letter
    return letters


def textToGcode(letters, text, lineLength, lineSpacing, padding, paperWidth, paperHeight, font_size=7.0, 
                z_height=2, travel_speed=8000, write_speed=4000, z_speed=2000):
    gcodeLettersArray = []
    offsetX, offsetY = padding, paperHeight - padding
    current_pen_up = True

    # Apply font scaling to letters
    scaled_letters = {}
    for char, letter in letters.items():
        scaled_letters[char] = letter.scaled(font_size)
    
    # Adjust line spacing based on font size
    adjusted_line_spacing = lineSpacing * font_size
    
    # Adjust padding between letters based on font size
    adjusted_padding = (padding * 0.5) * font_size

    # Calculate the maximum effective line length based on paper width
    max_line_length = min(lineLength, paperWidth - (2 * padding))

    # Initial setup commands
    gcodeLettersArray.extend([
        "G28 ; Home all axes",
        f"G0 Z{z_height} F{z_speed} ; Lift pen",
        f"G0 X{offsetX} Y{offsetY} F{travel_speed} ; Move to start position"
    ])

    # Split text into lines based on newline characters
    lines = text.split('\n')

    for line in lines:
        # Split the current line into words
        words = line.split()
        current_line = []
        current_line_width = 0

        for word in words:
            # Calculate width of this word including padding between letters
            word_width = sum(
                [scaled_letters[char].width + adjusted_padding for char in word if char in scaled_letters])

            # If this is the first word on the line or the line is empty
            if not current_line:
                # If single word is wider than max line length, we'll have to break it
                if word_width > max_line_length:
                    # Print the word character by character as much as fits
                    line_x = offsetX
                    for char in word:
                        if char not in scaled_letters:
                            continue

                        char_width = scaled_letters[char].width + adjusted_padding

                        # If this character would exceed the line width, go to next line
                        if line_x + char_width > paperWidth - padding:
                            # Go to next line - ALWAYS lift pen before moving to a new line
                            if not current_pen_up:
                                gcodeLettersArray.append(f"G0 Z{z_height} F{z_speed} ; Lift pen")
                                current_pen_up = True
                            
                            offsetY -= adjusted_line_spacing
                            if offsetY < padding:
                                break
                            line_x = padding
                            
                            # Now move to the new line position
                            gcodeLettersArray.append(
                                f"G0 X{line_x} Y{offsetY} F{travel_speed} ; New line")

                        # Print the character
                        letter = scaled_letters[char].translated(line_x, offsetY)
                        for instr in letter.instructions:
                            if instr.type == Instr.Type.write:
                                if current_pen_up:
                                    gcodeLettersArray.append(
                                        "G1 Z0 F500 ; Lower pen")
                                    current_pen_up = False
                                gcodeLettersArray.append(
                                    f"G1 X{instr.x:.2f} Y{instr.y:.2f} F{write_speed}")
                            else:
                                if not current_pen_up:
                                    gcodeLettersArray.append(
                                        f"G0 Z{z_height} F{z_speed} ; Lift pen")
                                    current_pen_up = True
                                gcodeLettersArray.append(
                                    f"G0 X{instr.x:.2f} Y{instr.y:.2f} F{travel_speed}")

                        line_x += char_width
                else:
                    # Word fits, add it to current line
                    current_line.append(word)
                    current_line_width = word_width
            else:
                # Check if adding this word would exceed line length
                space_width = scaled_letters[" "].width
                if current_line_width + space_width + word_width > max_line_length:
                    # Print current line
                    line_x = offsetX
                    for word_to_print in current_line:
                        for char in word_to_print:
                            if char not in scaled_letters:
                                continue

                            letter = scaled_letters[char].translated(line_x, offsetY)

                            for instr in letter.instructions:
                                if instr.type == Instr.Type.write:
                                    if current_pen_up:
                                        gcodeLettersArray.append(
                                            "G1 Z0 F500 ; Lower pen")
                                        current_pen_up = False
                                    gcodeLettersArray.append(
                                        f"G1 X{instr.x:.2f} Y{instr.y:.2f} F{write_speed}")
                                else:
                                    if not current_pen_up:
                                        gcodeLettersArray.append(
                                            f"G0 Z{z_height} F{z_speed} ; Lift pen")
                                        current_pen_up = True
                                    gcodeLettersArray.append(
                                        f"G0 X{instr.x:.2f} Y{instr.y:.2f} F{travel_speed}")

                            line_x += scaled_letters[char].width + adjusted_padding

                        # Add space after word
                        line_x += space_width

                    # Start new line - ALWAYS ensure pen is lifted before moving to a new line
                    if not current_pen_up:
                        gcodeLettersArray.append(f"G0 Z{z_height} F{z_speed} ; Lift pen")
                        current_pen_up = True
                    
                    offsetY -= adjusted_line_spacing
                    if offsetY < padding:
                        break

                    offsetX = padding
                    
                    # Now move to the new line position
                    gcodeLettersArray.append(
                        f"G0 X{offsetX} Y{offsetY} F{travel_speed} ; New line")

                    # Reset for new line
                    if word_width > max_line_length:
                        # Handle words that are too long for a single line
                        line_x = offsetX
                        for char in word:
                            if char not in scaled_letters:
                                continue

                            char_width = scaled_letters[char].width + adjusted_padding

                            # If this character would exceed the line width, go to next line
                            if line_x + char_width > paperWidth - padding:
                                # Go to next line - ALWAYS ensure pen is lifted
                                if not current_pen_up:
                                    gcodeLettersArray.append(f"G0 Z{z_height} F{z_speed} ; Lift pen")
                                    current_pen_up = True
                                    
                                offsetY -= adjusted_line_spacing
                                if offsetY < padding:
                                    break
                                line_x = padding
                                
                                # Now move to the new position
                                gcodeLettersArray.append(
                                    f"G0 X{line_x} Y{offsetY} F{travel_speed} ; New line")

                            # Print the character
                            letter = scaled_letters[char].translated(line_x, offsetY)
                            for instr in letter.instructions:
                                if instr.type == Instr.Type.write:
                                    if current_pen_up:
                                        gcodeLettersArray.append(
                                            "G1 Z0 F500 ; Lower pen")
                                        current_pen_up = False
                                    gcodeLettersArray.append(
                                        f"G1 X{instr.x:.2f} Y{instr.y:.2f} F{write_speed}")
                                else:
                                    if not current_pen_up:
                                        gcodeLettersArray.append(
                                            f"G0 Z{z_height} F{z_speed} ; Lift pen")
                                        current_pen_up = True
                                    gcodeLettersArray.append(
                                        f"G0 X{instr.x:.2f} Y{instr.y:.2f} F{travel_speed}")

                            line_x += char_width

                        current_line = []
                        current_line_width = 0
                    else:
                        # Word fits on a new line
                        current_line = [word]
                        current_line_width = word_width
                else:
                    # Add word to current line
                    current_line.append(word)
                    current_line_width += space_width + word_width  # Include space before word

        # Print last line if needed
        if current_line:
            line_x = offsetX
            for word_to_print in current_line:
                for char in word_to_print:
                    if char not in scaled_letters:
                        continue

                    letter = scaled_letters[char].translated(line_x, offsetY)

                    for instr in letter.instructions:
                        if instr.type == Instr.Type.write:
                            if current_pen_up:
                                gcodeLettersArray.append("G1 Z0 F500 ; Lower pen")
                                current_pen_up = False
                            gcodeLettersArray.append(
                                f"G1 X{instr.x:.2f} Y{instr.y:.2f} F{write_speed}")
                        else:
                            if not current_pen_up:
                                gcodeLettersArray.append(f"G0 Z{z_height} F{z_speed} ; Lift pen")
                                current_pen_up = True
                            gcodeLettersArray.append(
                                f"G0 X{instr.x:.2f} Y{instr.y:.2f} F{travel_speed}")

                    line_x += scaled_letters[char].width + adjusted_padding

                # Add space after word
                line_x += scaled_letters[" "].width

        # Move to the next line after processing a paragraph
        if not current_pen_up:
            gcodeLettersArray.append(f"G0 Z{z_height} F{z_speed} ; Lift pen")
            current_pen_up = True
        
        offsetY -= adjusted_line_spacing
        if offsetY < padding:
            break

        offsetX = padding
        gcodeLettersArray.append(
            f"G0 X{offsetX} Y{offsetY} F{travel_speed} ; New paragraph")

    # Lift pen at end
    if not current_pen_up:
        gcodeLettersArray.append(f"G0 Z{z_height} F{z_speed} ; Lift pen")
    
    # Move to home position at end
    gcodeLettersArray.append("G28 ; Return to home position")
    
    return "\n".join(gcodeLettersArray)

def parseArgs(namespace):
    argParser = argparse.ArgumentParser(fromfile_prefix_chars="@",
                                        description="Compiles text into 2D gcode for plotters")

    # Data options
    argParser.add_argument("-i", "--input", type=argparse.FileType('r'), default="-", metavar="FILE",
                           help="File to read characters from")
    argParser.add_argument("-o", "--output", type=argparse.FileType('w'), required=True, metavar="FILE",
                           help="File in which to save the gcode result")
    argParser.add_argument("-g", "--gcode-directory", type=str, default="./ascii_gcode/", metavar="DIR",
                           help="Directory containing the gcode information for all used characters")

    # Text options
    argParser.add_argument("-l", "--line-length", type=float, required=True,
                           help="Maximum length of a line")
    argParser.add_argument("-s", "--line-spacing", type=float, default=8.0,
                           help="Distance between two subsequent lines")
    argParser.add_argument("-p", "--padding", type=float, default=1.5,
                           help="Empty space between characters")
    argParser.add_argument("-f", "--font-size", type=float, default=1.0,
                           help="Font size scaling factor (default: 1.0)")

    # Paper dimension options
    argParser.add_argument("--paper-width", type=float, default=210.0,
                           help="Width of the paper (e.g., 210 for A4 in mm)")
    argParser.add_argument("--paper-height", type=float, default=297.0,
                           help="Height of the paper (e.g., 297 for A4 in mm)")
                           
    # Speed and height options
    argParser.add_argument("--z-height", type=float, default=2.5,
                           help="Z-axis travel height (default: 2.5mm)")
    argParser.add_argument("--travel-speed", type=float, default=8000,
                           help="Travel speed when pen is up (default: 8000mm/min)")
    argParser.add_argument("--write-speed", type=float, default=2000,
                           help="Writing speed when pen is down (default: 2000mm/min)")
    argParser.add_argument("--z-speed", type=float, default=2000,
                           help="Z-axis movement speed (default: 2000mm/min)")

    argParser.parse_args(namespace=namespace)


def main():
    class Args:
        pass
    parseArgs(Args)
    letters = readLetters(Args.gcode_directory)
    data = Args.input.read()
    # Pass the additional parameters to textToGcode
    gcode = textToGcode(letters, data, Args.line_length, Args.line_spacing, Args.padding,
                        Args.paper_width, Args.paper_height, Args.font_size,
                        Args.z_height, Args.travel_speed, Args.write_speed, Args.z_speed)
    Args.output.write(gcode)


if __name__ == '__main__':
    main()