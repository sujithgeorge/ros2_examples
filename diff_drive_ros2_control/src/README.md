## How to run

Build, source, launch as usual. Then give velocity command via keyboard using teleop_twist_keyboard as below:
$ ros2 run teleop_twist_keyboard teleop_twist_keyboard --ros-args -r /cmd_vel:=/diff_drive_controller/cmd_vel -p stamped:=true

## ros2 control commands that can be helpful in the context of this demo

$ ros2 control list_controller_types
$ ros2 control list_hardware_interfaces
$ ros2 control list_hardware_components
$ ros2 control list_controllers
If you did not gracefully exit a previous launch, some stray controllers (or some Gazebo controllers from a previous launch) might be lying around. Or parallel spawners can cause race conditions. Or another stack already running. For e.g. /gz_ros_control
You know this when you see in the console:
"Could not configure controller with name 'joint_state_broadcaster' because no controller with this name exists"
If so, run the 'ros2 control list_controllers'. The stray ones will appear, and you may have to kill them all.

Flow:

1.  In the ros2_control xacro file: mobile_base.ros2_control.xacro, we have a <ros2_control> tag as the second outermost (outermost being <robot>). Then inside it, in the <hardware> tag, we define the plugin which is a mock plugin.
    <hardware>
    <plugin>mock_components/GenericSystem</plugin>
    <param name="calculate_dynamics">true</param>
    </hardware>
    The calculate_dynamics true means that the encoders will return the velocity (which is going to be the same as the velocity we give as command) and the position of the joints (it does a simple calculation using the velocity to determine the joint rotation status of the wheel).
    Then we have two joint tags , one for each wheel.

     <joint name="base_right_wheel_joint">
             <command_interface name="velocity"/>
             <state_interface name="velocity"/>
             <state_interface name="position"/>
         </joint>
         <joint name="base_left_wheel_joint">
             <command_interface name="velocity"/>
             <state_interface name="velocity"/>
             <state_interface name="position"/>
         </joint>
         
         For each wheel, the command_interface is what we give it, and the state_interface is what it gives us back. In real world the command_interface would be converted to motor signals, and the state_interface (velocity and position) would be what the encoders provide back, so as to make it a closed loop. Note that the position is how much the wheel has rotated. This will not just be between 0 and 2π radians; it will keep accumulating beyond 2π after first rotation. This has nothing to do with odometry. It is to be noted that there is nothing in this XML, that denotes that this is a differential drive system. For this XML, these are just two separate independent joints. From the URDF, it knows that it is a 'continuous' joint, and it acts as a mock that receives velocity commands and gives back velocity and position state.

2.  Controller configuration is split across two YAML files (required on ROS 2 Jazzy):

    **ros2_control.yaml** — loaded only by `ros2_control_node`. Contains the manager settings:

        controller_manager:
            ros__parameters:
                update_rate: 50

    The update_rate: 50 means a 50 Hz read → update → write loop in controller_manager, which ties mock hardware, both controllers, and timing together.

    **my_robot_controllers.yaml** — passed to the spawner via `--param-file`. Each controller block includes its `type` and runtime params (Jazzy pattern; do not put controller types on `ros2_control_node`):

        joint_state_broadcaster:
            ros__parameters:
                type: joint_state_broadcaster/JointStateBroadcaster
                joints:
                  - base_left_wheel_joint
                  - base_right_wheel_joint

        diff_drive_controller:
            ros__parameters:
                type: diff_drive_controller/DiffDriveController

                left_wheel_names: ["base_left_wheel_joint"]
                right_wheel_names: ["base_right_wheel_joint"]

                wheel_separation: 0.45
                wheel_radius: 0.1

                odom_frame_id: "odom"
                base_frame_id: "base_footprint"

                pose_covariance_diagonal: [0.001, 0.001, 0.001, 0.001, 0.001, 0.01]
                twist_covariance_diagonal: [0.001, 0.001, 0.001, 0.001, 0.001, 0.01]

                enable_odom_tf: true
                publish_rate: 50.0

                linear.x.max_velocity: 1.0
                linear.x.min_velocity: -1.0
                angular.z.max_velocity: 1.0
                angular.z.min_velocity: -1.0

Source code for both JointStateBroadcaster and DiffDriveController is available on the github repo: ros-controls/ros2_controllers.

The main functions of the DiffDriveController are:

1. Register the left and right wheel joint names.
2. Accept a linear and angular velocity via the topic /diff_drive_controller/cmd_vel (This topic name is hardcoded into the source code of DiffDriveController (The /diff_drive_controller is the node name prefix, which is why it is prefixed before cmd_vel), so later on we will publish our velocity commands to this same topic name). The message type for this topic is TwistStamped. Because we need a stamped Twist message, we use the -p stamped:=true when we start out teleop_twist_keyboard.
3. Once it gets the linear and angular velocity via the /diff_drive_controller/cmd_vel topic, it uses the wheel_separation and wheel_radius to calculate the wheel velocity command for each wheel and sends it as a command to the real or mock hardware. In this demo, we are using mock.(Remember we defined <command_interface name="velocity"/> in the mock hardware setup in mobile_base.ros2_control.xacro)
4. It also calculates the odom, i.e. how much the robot would have moved from its original position. To do this, it 'reads' the state given back by the real / mock encoders. (Remember we defined <state_interface name="velocity"/> and <state_interface name="position"/> in the mock hardware setup in mobile_base.ros2_control.xacro). It uses this along with the wheel_separation and wheel_radius to calculate odom. We also need to define the odom_frame_id and the base_frame_id.
5. We have set enable_odom_tf: true. As a result of this, it will publish the odom to base frame tf. (The base frame name in this demo is base_footprint). The publish frequency is defined by publish_rate. Please note that the publish_rate is on individual controller level, but the update_rate is at a global level. The update_rate is the control loop rate.

For the JointStateBroadcaster, we select specific joints in my_robot_controllers.yaml (see above). If the `joints` list is omitted, JointStateBroadcaster publishes all available joint interfaces by default.

The main functions of the JointStateBroadcaster are:

1. 'Read' the state given back by the real / mock encoders. (Remember we defined <state_interface name="velocity"/> and <state_interface name="position"/> in the mock hardware setup in mobile_base.ros2_control.xacro). It is to be noted that DiffDriveController also reads the same. So whatever state_interface published by the mock / real hardware can be read by one or more controllers.
2. Publish the state to /joint_states. The robot_state_publisher would then read these /joint_states and publish the /tf. Along with this, the DiffDriveController will publish the odom to base frame (base_footprint in this demo) to /tf as well. All this combined will cause RViz to show the movement visual. The joint_states make the wheels rotate and the odom makes the robot move. Make sure you choose the fixed frame as odom in RViz.

In the my_robot.launch.xml, we first start robot_state_publisher. It is needed to load the robot_description and publish it. The ros2_control_node subscribes to this /robot_description to load hardware. The robot_state_publisher also looks at the joint_states and publish the /tf.

<node pkg="robot_state_publisher" exec="robot_state_publisher">
<param name="robot_description" value="$(command 'xacro $(var urdf_path)')"/>
</node>

We then start the controller manager with only ros2_control.yaml (which has only the update_rate in it, everything else is in my_robot_controllers.yaml)

    <node pkg="controller_manager" exec="ros2_control_node">
        <param from="$(find-pkg-share my_robot_bringup)/config/ros2_control.yaml"/>
    </node>

    Then we spawn both controllers in one spawner, passing my_robot_controllers.yaml via --param-file (Jazzy requirement):

        <node pkg="controller_manager" exec="spawner"
              args="joint_state_broadcaster diff_drive_controller --param-file $(var controllers_file)"/>

    On Jazzy, loading the full controller YAML into ros2_control_node causes spawner errors ("Controller already loaded" / configure failures). Controller `type` and params must go through the spawner's --param-file instead.

    Use a single spawner for all controllers (not two separate spawners) to avoid race conditions.

    Finally, we start RViz too:
    <node pkg="rviz2" exec="rviz2" output="screen" args="-d $(var rviz_config_path)"/>
