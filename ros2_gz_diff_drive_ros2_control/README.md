## How to run

Install the Gazebo ros2_control bridge if needed:

```bash
$ sudo apt install ros-jazzy-gz-ros2-control
```

Build, source, launch as usual:

```bash
$ ros2 launch robot_bringup_ros2_gz_diff_drive_ros2_control my_robot.launch.xml
```

Then give velocity command via keyboard using teleop_twist_keyboard as below. Note that we remap /cmd_vel to /diff_drive_controller/cmd_vel and set stamped:=true, because the diff_drive_controller is configured to accept stamped velocity messages.

```bash
$ ros2 run teleop_twist_keyboard teleop_twist_keyboard --ros-args -r /cmd_vel:=/diff_drive_controller/cmd_vel -p stamped:=true
```

Useful ros2_control inspection commands:

```bash
$ ros2 control list_controllers
$ ros2 control list_controller_types
$ ros2 control list_hardware_interfaces
$ ros2 control list_hardware_components
```

---

## Flow

Unlike the other demos in this repo, this one does not use the Gazebo DiffDrive plugin or a bridge.yaml for /cmd_vel, /joint_states, and /tf. Instead, Gazebo is connected to ROS2 through gz_ros2_control and the ros2_control controller manager.

1. When you press keys, the teleop_twist_keyboard publishes on /cmd_vel. Because of the remap above, this arrives on /diff_drive_controller/cmd_vel.

2. The diff_drive_controller (configured in my_robot_controllers.yaml) subscribes to /diff_drive_controller/cmd_vel and receives the linear and angular velocity commands.

   ```yaml
   diff_drive_controller:
     ros__parameters:
       type: diff_drive_controller/DiffDriveController

       left_wheel_names: ["base_left_wheel_joint"]
       right_wheel_names: ["base_right_wheel_joint"]

       wheel_separation: 0.45
       wheel_radius: 0.1

       odom_frame_id: "odom"
       base_frame_id: "base_footprint"

       enable_odom_tf: true
       use_stamped_vel: true
   ```

   The controller uses wheel_separation and wheel_radius to convert the twist command into a velocity command for each wheel joint.

3. These velocity commands are sent to the ros2_control hardware interface. In mobile_base.ros2_control.xacro, we have defined the hardware and the wheel joint interfaces as below:

   ```xml
   <ros2_control name="MobileBaseHardwareInterface" type="system">
       <hardware>
           <plugin>gz_ros2_control/GazeboSimSystem</plugin>
       </hardware>
       <joint name="base_right_wheel_joint">
           <command_interface name="velocity">
               <param name="min">-1</param>
               <param name="max">1</param>
           </command_interface>
           <state_interface name="velocity"/>
           <state_interface name="position"/>
       </joint>
       <joint name="base_left_wheel_joint">
           <command_interface name="velocity">
               <param name="min">-1</param>
               <param name="max">1</param>
           </command_interface>
           <state_interface name="velocity"/>
           <state_interface name="position"/>
       </joint>
   </ros2_control>
   ```

4. In mobile_base.gazebo.xacro, we load the gz_ros2_control plugin inside Gazebo. This plugin is the bridge between Gazebo physics and ros2_control. It loads only ros2_control.yaml, which configures the controller manager (update rate).

   ```xml
   <gazebo>
       <plugin filename="gz_ros2_control-system" name="gz_ros2_control::GazeboSimROS2ControlPlugin">
           <parameters>$(find robot_bringup_ros2_gz_diff_drive_ros2_control)/config/ros2_control.yaml</parameters>
       </plugin>
   </gazebo>
   ```

   The GazeboSimSystem hardware plugin applies the velocity commands from ros2_control to the wheel joints in the Gazebo physics engine, and reads back joint position and velocity state from the simulation.

5. The joint_state_broadcaster controller reads joint state from the hardware interface and publishes on /joint_states.

   ```yaml
   joint_state_broadcaster:
     ros__parameters:
       type: joint_state_broadcaster/JointStateBroadcaster
   ```

6. The robot_state_publisher node looks at the /joint_states topic and publishes the link TFs to the ROS2 topic /tf.

7. The diff_drive_controller also integrates wheel motion to estimate odometry and publishes the odom -> base_footprint TF to /tf (because enable_odom_tf is true). It also publishes on /odom.

8. The only topic bridged from Gazebo to ROS2 in this demo is /clock. This keeps the ROS2 time synced to the clock of the simulation.

   ```xml
   <node pkg="ros_gz_bridge" exec="parameter_bridge" output="screen"
         args="/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock"/>
   ```

   The /clock bridge keeps simulation time available on the ROS2 graph for nodes that subscribe to it.

---

## ros2_control configuration

Controller configuration is split across two YAML files (required on ROS 2 Jazzy):

**ros2_control.yaml** — loaded by the gz_ros2_control plugin. Contains only the controller manager settings:

```yaml
controller_manager:
  ros__parameters:
    update_rate: 50
```

**my_robot_controllers.yaml** — passed to the spawner via `--param-file`. Each controller block includes its `type` and params:

```yaml
joint_state_broadcaster:
  ros__parameters:
    type: joint_state_broadcaster/JointStateBroadcaster

diff_drive_controller:
  ros__parameters:
    type: diff_drive_controller/DiffDriveController

    left_wheel_names: ["base_left_wheel_joint"]
    right_wheel_names: ["base_right_wheel_joint"]

    wheel_separation: 0.45
    wheel_radius: 0.1

    odom_frame_id: "odom"
    base_frame_id: "base_footprint"

    enable_odom_tf: true
    publish_rate: 50.0
    use_stamped_vel: true
```

> On Jazzy, loading the full controller YAML into the controller manager causes spawner errors ("Controller already loaded" / configure failures). Controller `type` and params must go through the spawner's `--param-file` instead.

In the launch file, we spawn both controllers in one spawner after the robot is created in Gazebo:

```xml
<node pkg="controller_manager" exec="spawner" output="screen"
      args="joint_state_broadcaster diff_drive_controller --param-file $(var controllers_path)"/>
```

> Use a single spawner for all controllers (not two separate spawners) to avoid race conditions.

The joint_state_broadcaster makes /joint_states available for robot_state_publisher and RViz. The diff_drive_controller handles velocity commands and odometry.

---

## RViz configuration

RViz is launched with a saved config that shows the RobotModel display. Make sure the Fixed Frame is set to odom. As you drive the robot, you should see the model move in RViz.

---

## Launch file

We launch Gazebo simulation first. The world file is a simple empty world with a ground plane.

```xml
<include file="$(find-pkg-share ros_gz_sim)/launch/gz_sim.launch.py">
    <arg name="gz_args" value="$(var gazebo_world_path) -r"/>
</include>
```

We bridge only the simulation clock from Gazebo to ROS2.

```xml
<node pkg="ros_gz_bridge" exec="parameter_bridge" output="screen"
      args="/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock"/>
```

We launch the robot_state_publisher and give it the URDF file.

```xml
<node pkg="robot_state_publisher" exec="robot_state_publisher" output="screen">
    <param name="robot_description" value="$(command 'xacro $(var urdf_path)')"/>
</node>
```

This is the part which spawns the robot model inside gazebo sim. The create node reads the URDF from the /robot_description topic and spawns it as my_robot.

```xml
<node pkg="ros_gz_sim" exec="create" output="screen"
      args="-topic /robot_description -name my_robot"/>
```

We spawn the ros2_control controllers in one spawner, passing my_robot_controllers.yaml via `--param-file`.

```xml
<node pkg="controller_manager" exec="spawner" output="screen"
      args="joint_state_broadcaster diff_drive_controller --param-file $(var controllers_path)"/>
```

Finally we start RViz too.

```xml
<node pkg="rviz2" exec="rviz2" output="screen"
      args="-d $(var rviz_config_path)"/>
```

The launch file resolves paths to the two packages in this workspace:

```xml
<let name="urdf_path" value="$(find-pkg-share robot_bringup_ros2_gz_diff_drive_ros2_control_description)/urdf/my_robot.urdf.xacro"/>
<let name="rviz_config_path" value="$(find-pkg-share robot_bringup_ros2_gz_diff_drive_ros2_control_description)/rviz/urdf_config.rviz"/>
<let name="controllers_path" value="$(find-pkg-share robot_bringup_ros2_gz_diff_drive_ros2_control)/config/my_robot_controllers.yaml"/>
<let name="gazebo_world_path" value="$(find-pkg-share robot_bringup_ros2_gz_diff_drive_ros2_control)/config/gazebo_world.sdf"/>
```
