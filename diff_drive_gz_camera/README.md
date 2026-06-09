## How to run

Build, source, launch as usual. Then give velocity command via keyboard using teleop_twist_keyboard as below:

```bash
$ ros2 run teleop_twist_keyboard teleop_twist_keyboard
```

## Flow

1. When you press keys, the teleop_twist_keyboard publishes on /cmd_vel.
2. In the bridge.yaml , we have defined:
   - ros_topic_name: "/cmd_vel"
     gz_topic_name: "/model/my_robot/cmd_vel"
     ros_type_name: "geometry_msgs/msg/Twist"
     gz_type_name: "gz.msgs.Twist"
     direction: ROS_TO_GZ
     Because of this, this maps to the gazebo topic: /model/my_robot/cmd_vel
3. In mobile_base_gazebo.xacro, we have defined:
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
   This DiffDrive subscribes to the gazebo topic: /model/my_robot/cmd_vel and then rotates the wheel joints and thus moves the robot in Gazebo. The Gazebo physics engine does this by taking the linear and angular velocities from /model/my_robot/cmd_vel, and then using the wheel_separation and wheel_radius to calculate the velocity to be given to each of wheel joints.
   The DiffDrive also publishes the odom -> base_footprint TF in the gazebo topic: /model/my_robot/tf
4. The gazebo topic /model/my_robot/tf is mapped to the ROS2 topic /tf inside the bridge yaml.

- ros_topic_name: "/tf"
  gz_topic_name: "/model/my_robot/tf"
  ros_type_name: "tf2_msgs/msg/TFMessage"
  gz_type_name: "gz.msgs.Pose_V"
  direction: GZ_TO_ROS

5. We have defined JointStatePublisher below in mobile_base_gazebo macro.
   <gazebo>
   <plugin filename="gz-sim-joint-state-publisher-system" name="gz::sim::systems::JointStatePublisher">
   <joint_name>base_left_wheel_joint</joint_name>
   <joint_name>base_right_wheel_joint</joint_name>
   </plugin>
   </gazebo>
   JointStatePublisher publishes the joint states (Gazebo simulates an encoder) into the gazebo topic /world/empty/model/my_robot/joint_state. This is mapped to the ROS2 topic /joint_states inside the bridge yaml.
   - ros_topic_name: "/joint_states"
     gz_topic_name: "/world/empty/model/my_robot/joint_state"
     ros_type_name: "sensor_msgs/msg/JointState"
     gz_type_name: "gz.msgs.Model"
     direction: GZ_TO_ROS
6. The robot_state_publisher node of ROS2 looks at the /joint_states topic and publishes the TFs to the ROS2 topic /tf. But the odom -> base_footprint tf alone is published by DiffDrive in gazebo , and thereafter mapped to ROS2.
7. The mapping of clock from Gazebo to ROS2 keeps the ROS2 time synced to the clock of the simulation.
   - ros_topic_name: "/clock"
     gz_topic_name: "/clock"
     ros_type_name: "rosgraph_msgs/msg/Clock"
     gz_type_name: "gz.msgs.Clock"
     direction: GZ_TO_ROS
     You can use the use_sim_time for ROS2 nodes to use this sim clock instead of ROS2 wall clock. We have not done it in this demo, go ahead and do it in launch xml.

The camera feed happens in a parallel flow as below.

1.  In camera.xacro we have defined:
    <gazebo>
    <plugin filename="gz-sim-sensors-system" name="gz::sim::systems::Sensors">
    <render_engine>ogre</render_engine>
    </plugin>
    </gazebo>
2.  In the same camera.xacro file, we also configure the gazebo camera as below:
    <gazebo reference="camera_link">
    <sensor type="camera" name="camera">
    <camera>
    <horizontal_fov>1.3962634</horizontal_fov>
    ......
    ........
    <optical_frame_id>camera_link_optical</optical_frame_id>
    <camera_info_topic>camera/camera_info</camera_info_topic>
    </camera>
    <always_on>1</always_on>
    <update_rate>20</update_rate>
    <visualize>true</visualize>
    <topic>camera/image_raw</topic>

        </sensor>

    </gazebo>

    The optical_frame_id is the link id of the camera_link_optical in the URDF. In the URDF we have defined (inside camera.xacro)

    <link name="camera_link">
       ......
    </link>

    <joint name="base_camera_joint" type="fixed">
        <parent link="base_link" />
        <child link="camera_link" />
        <origin xyz="${(base_length + camera_length )/ 2.0} 0 ${base_height / 2.0}" rpy="0 0 0" />
    </joint>

    <link name="camera_link_optical" />

    <joint name="camera_optical_joint" type="fixed">
        <parent link="camera_link" />
        <child link="camera_link_optical" />
        <origin xyz="0 0 0" rpy="${-pi/2} 0 ${-pi/2}" />
    </joint>

    The reason we are not using camera_link directly as the optical_frame_id and instead using the camera_link_optical has to do with OpenCV.
    OpenCV uses different axes conventions, so we create a dummy link called camera_link_optical and then create a joint which flips the joint x-axis and z-axis to match OpenCV.

    The camera images will be published by Gazebo to the topic camera/image_raw, and the camera info will be published by Gazebo to the Gazebo topic camera/camera_info, because we configured it to be so above.
    Then in the bridge yaml, we map these to the corresponding ROS2 topics as below:
    - ros_topic_name: "/camera/camera_info"
      gz_topic_name: "/camera/camera_info"
      ros_type_name: "sensor_msgs/msg/CameraInfo"
      gz_type_name: "gz.msgs.CameraInfo"
      direction: GZ_TO_ROS

    - ros_topic_name: "/camera/image_raw"
      gz_topic_name: "/camera/image_raw"
      ros_type_name: "sensor_msgs/msg/Image"
      gz_type_name: "gz.msgs.Image"
      direction: GZ_TO_ROS

The lidar point cloud happens in a parallel flow as below.

1.  In lidar.xacro we have defined the lidar link and mounted it on top of base_link as below:

    <link name="lidar_link">
       ......
    </link>

    <joint name="base_lidar_joint" type="fixed">
        <parent link="base_link" />
        <child link="lidar_link" />
        <origin xyz="0 0 ${base_height + lidar_height / 2.0}" rpy="0 0 0" />
    </joint>

2.  In the same lidar.xacro file, we also configure the gazebo gpu_lidar sensor as below:
    <gazebo reference="lidar_link">
    <sensor type="gpu_lidar" name="lidar">
    <topic>lidar</topic>
    <update_rate>10</update_rate>
    <lidar>
    <scan>
    <horizontal>
    <samples>640</samples>
    ......
    <min_angle>-3.14159</min_angle>
    <max_angle>3.14159</max_angle>
    </horizontal>
    <vertical>
    <samples>16</samples>
    ......
    <min_angle>-0.261799</min_angle>
    <max_angle>0.261799</max_angle>
    </vertical>
    </scan>
    <range>
    <min>0.08</min>
    <max>10.0</max>
    </range>
    </lidar>
    <always_on>1</always_on>
    <visualize>true</visualize>
    </sensor>
    </gazebo>

    The gpu_lidar sensor uses the Sensors plugin that we already defined in camera.xacro. When we set the topic to lidar, Gazebo publishes the point cloud to the Gazebo topic lidar/points.
    Then in the bridge yaml, we map this to the corresponding ROS2 topic as below:
    - ros_topic_name: "/lidar/points"
      gz_topic_name: "/lidar/points"
      ros_type_name: "sensor_msgs/msg/PointCloud2"
      gz_type_name: "gz.msgs.PointCloudPacked"
      frame_id: "lidar_link"
      direction: GZ_TO_ROS

    The frame_id is set to lidar_link so that RViz can place the point cloud correctly in the TF tree.

   ## RViz configuration
    For the camera, in RViz, you can do 'Add' and in the 'By Display Type', you can choose 'Image'. For some reason, choosing Camera causes a flickering video.
    For the lidar, in RViz, you can do 'Add' and in the 'By Display Type', you can choose 'PointCloud2'. Set the topic to /lidar/points. Make sure the Fixed Frame is set to odom.

## Launch file

We launch the robot_state_publisher and give it the URDF file.
<node pkg="robot_state_publisher" exec="robot_state_publisher">

<param name="robot_description" value="$(command 'xacro $(var urdf_file_path)')"/>
</node>

We launch gazebo simulation as below. Note that the world file that we give gazebo is almost like the Gazebo empty world sdf file. We just added a dining table object to it and saved the sdf so that we don't have to do it each time. The ros-gz-sim package folder is inside /opt/ros/jazzy/share usually. The find-pkg-share will find it.

  <include file="$(find-pkg-share ros_gz_sim)/launch/gz_sim.launch.py">
    <arg name="gz_args" value="$(var gazebo_world_file_path) -r"/>
  </include>

This is the bridge between ROS2 and gazebo and the configuration is done in bridge.yaml

  <node pkg="ros_gz_bridge" exec="parameter_bridge">
    <param name="config_file" value="$(var bridge_config_file_path)"/>
  </node>

This is the part which spawns the robot model inside gazebo sim.
<node pkg="ros_gz_sim" exec="create" args="-topic /robot_description"/>

Finally we start RViz too.
<node pkg="rviz2" exec="rviz2" args="-d $(var rviz_config_file_path)"/>
