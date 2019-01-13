#!/usr/bin/python3
# non_planar.py
# dan woolsey
#
# script to generate more precise z axis displacement values built on a
# template for gcode post processing

import fileinput
import re
import sys

import math as m

PI = m.pi

# all distance values are measured in (mm)
parameters = {"wave_amplitude": 2.0,
              "wave_length": 20.0,
              "wave_length_2": 200.0,
              "wave_in": 0.4,
              "wave_out": 30.0,
              "wave_ramp": 10,
              "wave_digits": 4,
              "bed_center_x": 0,
              "bed_center_y": 0,
              "wave_function": "wave" # 2 functions currently implemented: wave and wing
              }

gcodeX = 0
gcodeY = 0
gcodeZ = 0
gcodeE = 0
gcodeF = 4500
lastGcodeX = gcodeX
lastGcodeY = gcodeY
lastGcodeZ = gcodeZ
lastGcodeE = gcodeE
lastGcodeF = gcodeF

input_buffer = []
output_buffer = []

# MATHS
# Various functions required for calculations

def dist3(x1,y1,z1,x2,y2,z2):
    return m.sqrt(m.pow(x2-x1,2.0) + m.pow(y2-y1,2.0) + m.pow(z2-z1,2.0))

def dist2(x1,y1,x2,y2):
    return m.sqrt(m.pow(x2-x1,2.0) + m.pow(y2-y1,2.0))

def dist1(s1,s2):
    return abs(s2-s1)

def digitise(num, digits):
    factor = 10^digits
    return float(round(num*factor)/factor)

def calculate_ramps(z):
    rampA = max(min(((z-parameters["wave_in"])/(parameters["wave_ramp"])),1.0),0.0)
    rampB = 1.0 - (max(min(((z-parameters["wave_out"]+parameters["wave_ramp"])/parameters["wave_ramp"]),1.0),0.0))
    return rampA * rampB

def calculate_z_displacement(x,y,z):
    ramps = calculate_ramps(z)
    z_offset = 0
    amplitude = parameters["wave_amplitude"]
    bed_center_x = parameters["bed_center_x"]
    bed_center_y = parameters["bed_center_y"]
    wave_length = parameters["wave_length"]
    wave_length_2 = parameters["wave_length_2"]
    if(parameters["wave_function"] == "wave"):
        z_offset = 0.0 - amplitude/2.0 + (amplitude/(4.0*m.sin(((x-bed_center_x)*2.0*PI)/wave_length))) + (amplitude/(4.0*m.sin(((y-bed_center_y)*2.0*PI)/wave_length)))
    elif(parameters["wave_function"] == "wing"):
        y_displacement = y - bed_center_y - (wave_length_2/4)
        z_offset = -amplitude/2.0 + amplitude * (m.sin(m.pow((((x-bed_center_x)*m.sqrt(PI))/amplitude - (m.sqrt(PI)/2.0)),2.0))) * (1.0 + 0.5*m.cos((2.0*PI*y_displacement)/wave_length_2))
    elif(parameters["wave_function"]):
        return eval(parameters["wave_function"])
    else:
        print("> no wave function found")
    z_offset *= ramps
    return z_offset

def calculate_extrusion_multiplier(x,y,z):
    ramps = calculate_ramps(z)
    layer_height = 1.0 # must be 1 because divide by 0 error
    # this will be an issue
    if(parameters["wave_function"] == "wave"):
        layer_height = y - parameters["bed_center_y"] - (parameters["wave_length"]/4.0)
    elif(parameters["wave_function"] == "wing"):
        layer_height = y - parameters["bed_center_y"] - (parameters["wave_length_2"]/4.0)
    else:
        print("cannot calculate y_displacement without extra parameters for user defined wave_function")
    this = calculate_z_displacement(x,y,z)
    last = calculate_z_displacement(x,y,(z-layer_height))
    multiplier = 1.0 + ((this-last)/layer_height)
    return multiplier

def displace_move(line,x,y,z,e,f): # optional verbose argument for ...
    if(gcodeZ >= parameters["wave_in"] and gcodeZ <= parameters["wave_out"]):
        op_x = x or lastGcodeX
        op_y = y or lastGcodeY
        op_z = z or lastGcodeZ
        op_e = e or lastGcodeE
        op_f = f or lastGcodeF

        distance = dist2(lastGcodeX, lastGcodeY, op_x, op_y)
        segments = max(m.ceil(distance/parameters["wave_max_segment_length"]),1)

        gcode = "; displaced move start (" + segments + "segments)\n"

        for(k=0, k<segments; k++):
            segmentX = (lastGcodeX + (k+1)) * ((op_x - lastGcodeX)/segments)
            segmentY = (lastGcodeY + (k+1)) * ((op_y - lastGcodeY)/segments)
            segmentZ = (lastGcodeZ + (k+1)) * ((op_z - lastGcodeZ)/segments)
            segmentE = gcodeE/segments # only for relative extrusion

            segmentE *= calculate_extrusion_multiplier(segmentX, segmentY, segmentZ)
            segmentZ += calculate_z_displacement(segmentX, segmentY, segmentZ)

            wave_digits = parameters["wave_digits"]

            gcode += "G1"
            gcode += " X" + str(digitise(segmentX, wave_digits))
            gcode += " Y" + str(digitise(segmentY, wave_digits))
            gcode += " Z" + str(digitise(segmentZ, wave_digits))
            gcode += " E" + str(digitise(segmentE, wave_digits))
            gcode += " F" + str(op_f)
            gcode += " ; segment " + str(k) + "\n"
        gcode += " ; displaced move end \n"
        return gcode
    else:
        return line

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
    return displace_move(line,x=0.0,y=0.0,z,e=0.0,f=0.0)

def process_retraction_move(line, e, f):
    # do stuff
    return line

def process_printing_move(line, x, y, z, e, f):
    #print("process_printing_move: " + line + " - " + str(x) + ',' + str(y) + ',' + str(z) + ',' + str(e) + ',' + str(f))
    # do stuff
    return displace_move(line,x,y,z,e,f)

def process_travel_move(line, x, y, z, f):
    # do stuff
    return displace_move(line,x,y,z,e=0.0,f)

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

# testing area

def test_set_1():
    print("> dist3() = " + str(dist3(24.3, 56.4, 2.13, 11, 64.5, 34.1)))
    print("> dist2() = " + str(dist2(56.32, 24, 76.2, 12)))
    print("> dist1() = " + str(dist1(23.4, 19.3)))
    print("> digitise() = " + str(digitise(45.32, 4)))
    print("> calculate_ramps() = " + str(calculate_ramps(2)))
    print("> calculate_z_displacement() = " + str(calculate_z_displacement(4,8,3)))
    print("> calculate_extrusion_multiplier() = " + str(calculate_extrusion_multiplier(16,24,9)))


# main loop

def main():
    with fileinput.input() as f:
        for line in f: # iterates line by line for file in sys.argv[1]
            #print(line,end='')
            line = line.strip('\n') # need to check if this is ok
            filter_parameters(line)
            input_buffer.append(line)
        process_buffer()
        init()

if __name__ == "__main__":
    #main()
    test_set_1()
