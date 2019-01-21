# Slice Processing

Toolset written for dissertation on Non-Planar FDM and Dual Extrusion 3D Printing

***

## Usage

There are 2 main files: `post_processing.py` and `non_planar.py`. The first is a
template ideal for a user to insert their own functions to perform basic data
processing on the GCode obtained from the slicer. The second takes user-defined
parameters and caulculates the displacement of each movement (x,y,z) to a set
level of accuracy: `parameters["wave_digits"]`

Most 3D printing software environments allow for post processing scripts to be added
when generating GCode from an STL file.

***

## Related Work

[Moritz Walter - GCode Post Processing](https://hackaday.com/2016/07/20/3d-printering-g-code-post-processing-with-perl/)

[Moritz Walter - Non Planar FDM](https://hackaday.com/2016/07/27/3d-printering-non-planar-layer-fdm/)

[Nadiyapara et al, A Review of Variable Slicing in FDM](https://link.springer.com/article/10.1007/s40032-016-0272-7)

[Daniel Ahler, Non-Planar Layers for Smooth Surface Generation](https://tams.informatik.uni-hamburg.de/lehre/2018ws/seminar/tams/doc/Daniel_Ahlers_nonplanar_slicing_20181127.pdf)
