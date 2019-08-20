Introduction
============

 The trace-cmd command interacts only with the Ftrace tracer that is built inside the Linux kernel. It is a user-space front-end command-line tool for Ftrace. However Ftrace is not enough to analysis performance problem. We need to use systrace and perf tools with the trace-cmd to optimize the performance in android systems. 
 We can store a dataframe object in pandas with the raw data in Ftrace using the trace-cmd, but it is disable in the case of the systrace. So this systrace parser llbrary support a way to store a dataframe with the raw data in systrace, likes the trace-cmd. 


Motivations
===========

The main goals of Systrace Parser are:
-  Support analysis of systrace to be taken from android devices.
-  Get insights on what's working on the linux scheduler.
-  Enables kernel developers to analysis the delayed points.


Install
=======

This systrace parser use some pyhton libraries, numpy and pandas. So those should be included in your local computer.

pip install numpy</br>
pip install pandas


External Links
==============

- Linux Integrated System Analysis (LISA) & Friends [Slides](http://events.linuxfoundation.org/sites/events/files/slides/ELC16_LISA_20160326.pdf) and [Video](https://www.youtube.com/watch?v=yXZzzUEngiU)
  Note: the LISA classes referred by the slides are outdated, but all the other concepts and the overall architecture stays the same.
- Some insights on what it takes to have reliable tests: [Video](https://www.youtube.com/watch?v=I_MZ9XS3_zc&t=7s)
