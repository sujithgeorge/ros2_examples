## How to run

To move robot:
$ ros2 run teleop_twist_keyboard teleop_twist_keyboard

To move arms:
$ ros2 topic pub --once /joint0/cmd_pos std_msgs/msg/Float64 "{data: 1.0}"
$ ros2 topic pub --once /joint1/cmd_pos std_msgs/msg/Float64 "{data: 0.5}"
