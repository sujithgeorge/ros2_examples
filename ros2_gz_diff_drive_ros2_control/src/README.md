## Gazebo simulation (gz_ros2_control)

Install the Gazebo ros2_control bridge if needed:

```bash
sudo apt install ros-jazzy-gz-ros2-control
```

Launch Gazebo with the robot:

```bash
ros2 launch my_robot_bringup my_robot.launch.xml
```

## Moving the robot

```bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard --ros-args -r /cmd_vel:=/diff_drive_controller/cmd_vel -p stamped:=true
```

## ros2 control commands

```bash
ros2 control list_controllers
ros2 control list_controller_types
ros2 control list_hardware_interfaces
ros2 control list_hardware_components
```
