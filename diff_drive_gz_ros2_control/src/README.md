## Moving the robot

$ ros2 run teleop_twist_keyboard teleop_twist_keyboard --ros-args -r /cmd_vel:=/diff_drive_controller/cmd_vel -p stamped:=true

## ros2 control commands

$ ros2 control list_controllers

$ ros2 control list_controller
$ ros2 control list_controller_types

$ ros2 control list_hardware_interfaces
$ ros2 control list_hardware_components
