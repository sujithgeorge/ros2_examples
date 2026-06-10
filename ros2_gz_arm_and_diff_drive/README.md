## How to run

Build, source, launch as usual. Then give velocity command via keyboard using teleop_twist_keyboard as below:

```bash
$ ros2 run teleop_twist_keyboard teleop_twist_keyboard
```

To move the arm joints, publish position commands as below. joint0 controls the arm_base -> forearm joint, and joint1 controls the forearm -> hand joint. Both joints have a range of 0 to pi/2 radians.

```bash
$ ros2 topic pub --once /joint0/cmd_pos std_msgs/msg/Float64 "{data: 1.0}"
$ ros2 topic pub --once /joint1/cmd_pos std_msgs/msg/Float64 "{data: 0.5}"
```

---

## Flow

1. When you press keys, the teleop_twist_keyboard publishes on /cmd_vel.

2. In the bridge.yaml , we have defined:

   ```yaml
   - ros_topic_name: "/cmd_vel"
     gz_topic_name: "/model/my_robot/cmd_vel"
     ros_type_name: "geometry_msgs/msg/Twist"
     gz_type_name: "gz.msgs.Twist"
     direction: ROS_TO_GZ
   ```

   Because of this, this maps to the gazebo topic: /model/my_robot/cmd_vel

3. In mobile_base_gazebo.xacro, we have defined:

   ```xml
   <gazebo>
       <plugin filename="gz-sim-diff-drive-system" name="gz::sim::systems::DiffDrive">
           <left_joint>base_left_wheel_joint</left_joint>
           <right_joint>base_right_wheel_joint</right_joint>
           <wheel_separation>0.45</wheel_separation>
           <wheel_radius>0.1</wheel_radius>
           <frame_id>odom</frame_id>
           <child_frame_id>base_footprint</child_frame_id>
       </plugin>
   </gazebo>
   ```

   This DiffDrive subscribes to the gazebo topic: /model/my_robot/cmd_vel and then rotates the wheel joints and thus moves the robot in Gazebo. The Gazebo physics engine does this by taking the linear and angular velocities from /model/my_robot/cmd_vel, and then using the wheel_separation and wheel_radius to calculate the velocity to be given to each of wheel joints.

   The DiffDrive also publishes the odom -> base_footprint TF in the gazebo topic: /model/my_robot/tf

4. The gazebo topic /model/my_robot/tf is mapped to the ROS2 topic /tf inside the bridge yaml.

   ```yaml
   - ros_topic_name: "/tf"
     gz_topic_name: "/model/my_robot/tf"
     ros_type_name: "tf2_msgs/msg/TFMessage"
     gz_type_name: "gz.msgs.Pose_V"
     direction: GZ_TO_ROS
   ```

5. We have defined JointStatePublisher below in mobile_base_gazebo macro.

   ```xml
   <gazebo>
       <plugin filename="gz-sim-joint-state-publisher-system" name="gz::sim::systems::JointStatePublisher">
           <joint_name>base_left_wheel_joint</joint_name>
           <joint_name>base_right_wheel_joint</joint_name>
       </plugin>
   </gazebo>
   ```

   JointStatePublisher publishes the joint states (Gazebo simulates an encoder) into the gazebo topic /world/empty/model/my_robot/joint_state. This is mapped to the ROS2 topic /joint_states inside the bridge yaml.

   ```yaml
   - ros_topic_name: "/joint_states"
     gz_topic_name: "/world/empty/model/my_robot/joint_state"
     ros_type_name: "sensor_msgs/msg/JointState"
     gz_type_name: "gz.msgs.Model"
     direction: GZ_TO_ROS
   ```

6. The robot_state_publisher node of ROS2 looks at the /joint_states topic and publishes the TFs to the ROS2 topic /tf. But the odom -> base_footprint tf alone is published by DiffDrive in gazebo , and thereafter mapped to ROS2.

7. The mapping of clock from Gazebo to ROS2 keeps the ROS2 time synced to the clock of the simulation.

   ```yaml
   - ros_topic_name: "/clock"
     gz_topic_name: "/clock"
     ros_type_name: "rosgraph_msgs/msg/Clock"
     gz_type_name: "gz.msgs.Clock"
     direction: GZ_TO_ROS
   ```

   You can use the use_sim_time for ROS2 nodes to use this sim clock instead of ROS2 wall clock. We have not done it in this demo, go ahead and do it in launch xml.

---

## Arm

The arm control happens in a parallel flow as below.

1. In arm.xacro we have defined the arm links and mounted the arm on top of base_link as below:

   ```xml
   <link name="arm_base">
       ......
   </link>

   <link name="forearm">
       ......
   </link>

   <link name="hand">
       ......
   </link>

   <joint name="base_arm_joint" type="fixed">
       <parent link="base_link" />
       <child link="arm_base" />
       <origin xyz="${base_length / 4.0} 0 ${ base_height + (arm_base_height / 2.0)}" rpy="0 0 0" />
   </joint>

   <joint name="arm_base_forearm_joint" type="revolute">
       <parent link="arm_base" />
       <child link="forearm" />
       <origin xyz="0 0 ${arm_base_height/2}" rpy="0 0 0" />
       <axis xyz="0 1 0" />
       <limit lower="0" upper="${pi/2}" velocity="100" effort="100" />
   </joint>

   <joint name="forearm_hand_joint" type="revolute">
       <parent link="forearm" />
       <child link="hand" />
       <origin xyz="0 0 ${forearm_length}" rpy="0 0 0" />
       <axis xyz="0 1 0" />
       <limit lower="0" upper="${pi/2}" velocity="100" effort="100" />
   </joint>
   ```

2. In the same arm.xacro file, we also configure the gazebo JointPositionController plugins for each revolute joint as below:

   ```xml
   <gazebo>
       <plugin filename="gz-sim-joint-position-controller-system" name="gz::sim::systems::JointPositionController">
           <joint_name>arm_base_forearm_joint</joint_name>
           <p_gain>5</p_gain>
       </plugin>
   </gazebo>
   <gazebo>
       <plugin filename="gz-sim-joint-position-controller-system" name="gz::sim::systems::JointPositionController">
           <joint_name>forearm_hand_joint</joint_name>
           <p_gain>3</p_gain>
       </plugin>
   </gazebo>
   ```

   Each JointPositionController subscribes to a gazebo topic of the form /model/my_robot/joint/<joint_name>/0/cmd_pos and moves the joint to the commanded position using a P controller.

   We publish position commands from ROS2 on /joint0/cmd_pos and /joint1/cmd_pos. Then in the bridge yaml, we map these to the corresponding gazebo topics as below:

   ```yaml
   - ros_topic_name: "/joint0/cmd_pos"
     gz_topic_name: "/model/my_robot/joint/arm_base_forearm_joint/0/cmd_pos"
     ros_type_name: "std_msgs/msg/Float64"
     gz_type_name: "gz.msgs.Double"
     direction: ROS_TO_GZ

   - ros_topic_name: "/joint1/cmd_pos"
     gz_topic_name: "/model/my_robot/joint/forearm_hand_joint/0/cmd_pos"
     ros_type_name: "std_msgs/msg/Float64"
     gz_type_name: "gz.msgs.Double"
     direction: ROS_TO_GZ
   ```

3. We have also defined a JointStatePublisher for the arm joints in arm.xacro.

   ```xml
   <gazebo>
       <plugin filename="gz-sim-joint-state-publisher-system" name="gz::sim::systems::JointStatePublisher">
           <joint_name>arm_base_forearm_joint</joint_name>
           <joint_name>forearm_hand_joint</joint_name>
       </plugin>
   </gazebo>
   ```

   This publishes the arm joint states into the same gazebo topic /world/empty/model/my_robot/joint_state that the wheel JointStatePublisher uses. The bridge yaml maps this to the ROS2 topic /joint_states, and robot_state_publisher uses these joint positions to publish the arm link TFs.

---

## RViz configuration

RViz is launched with a saved config that shows the RobotModel display. Make sure the Fixed Frame is set to odom. As you drive the robot and move the arm joints, you should see the model update in RViz.

---

## Launch file

We launch the robot_state_publisher and give it the URDF file.

```xml
<node pkg="robot_state_publisher" exec="robot_state_publisher">
    <param name="robot_description" value="$(command 'xacro $(var urdf_file_path)')"/>
</node>
```

We launch gazebo simulation as below. Note that the world file that we give gazebo is almost like the Gazebo empty world sdf file. We just added a dining table object to it and saved the sdf so that we don't have to do it each time. The ros-gz-sim package folder is inside /opt/ros/jazzy/share usually. The find-pkg-share will find it.

```xml
<include file="$(find-pkg-share ros_gz_sim)/launch/gz_sim.launch.py">
    <arg name="gz_args" value="$(var gazebo_world_file_path) -r"/>
</include>
```

This is the bridge between ROS2 and gazebo and the configuration is done in bridge.yaml

```xml
<node pkg="ros_gz_bridge" exec="parameter_bridge">
    <param name="config_file" value="$(var bridge_config_file_path)"/>
</node>
```

This is the part which spawns the robot model inside gazebo sim.

```xml
<node pkg="ros_gz_sim" exec="create" args="-topic /robot_description"/>
```

Finally we start RViz too.

```xml
<node pkg="rviz2" exec="rviz2" args="-d $(var rviz_config_file_path)"/>
```
