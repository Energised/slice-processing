#!/usr/bin/python3
# post_processing.py
# dan woolsey
#
# script template based on perl code in this directory

import fileinput
import re
import sys

parameters = {}

input_buffer = []
output_buffer = []

# REGULAR EXPRESSIONS
# For use in filter_print_gcode

comment_r = re.compile('^\s*;(.*)\s*')

tool_r = re.compile('^T(\d)(\s*;\s*([\s\w_-]*)\s*)?')

pos_re = re.compile("^G[01](\s+X(-?\d*\.?\d+))?(\s+Y(-?\d*\.?\d+))?(\s+Z(-?\d*\.?\d+))?"
                        + "(\s+E(-?\d*\.?\d+))?(\s+F(-?\d*\.?\d+))?(\s*;\s*([\h\w_-]*)\s*)?")

g92_re = re.compile("^G92(\s+X(-?\d*\.?\d+))?(\s*Y(-?\d*\.?\d+))?(\s+Z(-?\d*\.?\d+))?"
                      + "(\s+E(-?\d*\.?\d+))?(\s*;\s*([\s\w_-]*)\s*)?")

m82_re = re.compile("^M82(\s*;\s*([\s\w_-]*)\s*)?")

m83_re = re.compile("^M83(\s*;\s*([\s\w_-]*)\s*)?")

end_re = re.compile("^; end of print")

other_re = re.compile(".*(\s*([\s\w_-]*)\s*)?")

# INITIALISE
# For initialising values based on printing parameters

def init():
    with open("output.gcode", "w+") as o:
        for line in output_buffer:
            o.write(line + "\n")
        print("Output written to: output.gcode")

# SUBROUTINES
# Available methods to handle individual lines of gcode

def process_start_gcode(line):
    line_new = line
    # will do something
    return line_new

def process_end_gcode(line):
    line_new = line
    # will do something
    return line_new

def process_tool_change(line, tool):
    print("process_tool_change: " + line + " - " + tool)
    # do stuff
    return line

def process_comment(line, comment):
    print("process_comment: " + line + " - " + comment)
    # do stuff
    return line

def process_layer_change(line, z):
    # do stuff
    return line

def process_retraction_move(line, e, f):
    # do stuff
    return line

def process_printing_move(line, x, y, z, e, f):
    print("process_printing_move: " + line + " - " + str(x) + ',' + str(y) +
          ',' + str(z) + ',' + str(e) + ',' + str(f))
    # do stuff
    return line

def process_travel_move(line, x, y, z, f):
    # do stuff
    return line

def process_absolute_extrusion(line):
    # do stuff
    return line

def process_relative_extrusion(line):
    # do stuff
    return line

def process_touch_off(line, x, y, z, e):
    # do stuff
    return line

def process_other(line):
    # do stuff
    return line

# PROCESSING LINES

def filter_parameters(line):

    """ Collects parameters from gcode comments """

    param_r1 = re.compile('^\s*;\s*([\w_-]*)\s*=\s*(\d*\.?\d+)\s*')
    param_r2 = re.compile('^\s*;\s*([\s\w_-]*)\s*=\s*(.*)\s*')
    param_val = param_r1.match(line) # check for parameter values in gcode
    param_str = param_r2.match(line)
    if param_val:
        print('1')
        param = param_val.group().split() # turn line into a list
        #print(param)
        key = param[1]
        value = float(param[3])
        if not value == 0:
            if not key in parameters:
                parameters[key] = value
    elif param_str:
        print('2')
        param = param_str.group().split()
        key = param[1]
        value = param[3]
        parameters[key] = value

def process_buffer():

    """ Applies the subroutines modifications to input_buffer and
        appends the new line to output_buffer """

    start = 0
    end = 0
    start_r = re.compile('^; start of print')
    end_r = re.compile('^; end of print')
    for line in input_buffer:
        #print('process_buffer: ' + line)
        start_t = start_r.match(line)
        end_t = end_r.match(line)
        if start_t: # if start of print
            start = 1
        if end_t: # if end of print
            end = 1

        if start == 0: # if first time running and have extra start code
            line_new = process_start_gcode(line)
            output_buffer.append(line_new)
        elif end == 1:
            line_new = process_end_gcode(line)
            output_buffer.append(line_new)
        else:
            line_new = filter_print_gcode(line)
            output_buffer.append(line_new)

def filter_print_gcode(line):

    """ Filters gcode and handles appropriate subroutine calls """

    split_line = line.split() # turn line into a list of args
    #print(split_line)
    if comment_r.match(line):
        comment = ' '.join(split_line[1:]) # seperate each list item with a space
        return process_comment(line, comment)
    elif tool_r.match(line):
        tool = line.strip('T') # remove the T to get the tool value (CHECK IN NEED THE T IN THE VAR)
        return process_tool_change(line, tool)
    elif pos_re.match(line):
        x,y,z,e,f = -1,-1,-1,-1,-1
        print("filter print gcode: " + str(split_line)) # this is all wrong, REDO!!!!
        try:
            x = split_line[1].strip('X') # so need to test for if the argument has x, y, z, e, f in it
            y = split_line[2].strip('Y') # so can choose appropriate function`
            z = split_line[3].strip('Z')
            e = split_line[4].strip('E')
            f = split_line[5].strip('F')
        except IndexError as i:
            pass
        if e:
            if (x or y or z):
                return process_printing_move(line, x, y, z, e, f)
            else:
                return process_retraction_move(line, e, f)
        else:
            if (z and not(x or y)):
                return process_layer_change(line, z, f)
            else:
                return process_travel_move(line, x, y, z, f)
    elif g92_re.match(line):
        x = split_line[1].strip('X')
        y = split_line[2].strip('Y')
        z = split_line[3].strip('Z')
        e = split_line[4].strip('E')
        return process_touch_off(line, x, y, z, e)
    elif m82_re.match(line):
        return process_absolute_extrusion(line)
    elif m83_re.match(line):
        return process_relative_extrusion(line)
    else:
        if other_re.match(line):
            return process_other(line)


# main loop
with fileinput.input() as f:
    for line in f: # iterates line by line for file in sys.argv[1]
        #print(line,end='')
        line = line.strip('\n') # need to check if this is ok
        filter_parameters(line)
        input_buffer.append(line)
    process_buffer()
    init()
