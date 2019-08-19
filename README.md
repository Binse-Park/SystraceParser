Introduction
============

The trace-cmd command interacts only with the Ftrace tracer that is built inside the Linux kernel. It is a user-space front-end command-line tool for Ftrace. But we need to use sometimes with systrace to optimize the performance in some systems. So we need a tool to parsing the systrace to be simiar with trace-cmd.


Motivations
===========

The main goals of Systrace Parser are:
-  Support analysis of systrace to be taken from android devices.
-  Get insights on what's working on the linux scheduler.
-  Enables kernel developers to analysis the delayed points.


Install
=======

pip install numpy
pip install pandas


External Links
==============

- Linux Integrated System Analysis (LISA) & Friends [Slides](http://events.linuxfoundation.org/sites/events/files/slides/ELC16_LISA_20160326.pdf) and [Video](https://www.youtube.com/watch?v=yXZzzUEngiU)
  Note: the LISA classes referred by the slides are outdated, but all the other concepts and the overall architecture stays the same.
- Some insights on what it takes to have reliable tests: [Video](https://www.youtube.com/watch?v=I_MZ9XS3_zc&t=7s)
