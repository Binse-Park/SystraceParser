Introduction
============

The trace-cmd command interacts only with the Ftrace tracer that is built inside the Linux kernel. It is a user-space front-end command-line tool for Ftrace. But we need to use sometimes with systrace to optimize the performance in some systems. So we need a tool to parsing the systrace to be simiar with trace-cmd.


Motivations
===========

The main goals of Systrace Parser are:
-  Support analysis of systrace to be taken from android devices.
-  Gatherring the app entry time adn calculating statistics.


Install
=======

pip install numpy
pip install pandas
