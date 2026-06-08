from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, RegisterEventHandler
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, FindExecutable, LaunchConfiguration, PathJoinSubstitution

from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    use_sim_time = LaunchConfiguration('use_sim_time', default='true')

    urdf_path = PathJoinSubstitution([
        FindPackageShare('my_robot_description'),
        'urdf',
        'my_robot.urdf.xacro',
    ])

    robot_description = {
        'robot_description': Command([
            PathJoinSubstitution([FindExecutable(name='xacro')]),
            ' ',
            urdf_path,
        ])
    }

    robot_controllers = PathJoinSubstitution([
        FindPackageShare('my_robot_bringup'),
        'config',
        'my_robot_controllers.yaml',
    ])

    gazebo_world = PathJoinSubstitution([
        FindPackageShare('my_robot_bringup'),
        'config',
        'gazebo_world.sdf',
    ])

    rviz_config = PathJoinSubstitution([
        FindPackageShare('my_robot_description'),
        'rviz',
        'urdf_config.rviz',
    ])

    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='screen',
        parameters=[robot_description, {'use_sim_time': use_sim_time}],
    )

    rviz = Node(
        package='rviz2',
        executable='rviz2',
        output='screen',
        arguments=['-d', rviz_config],
        parameters=[{'use_sim_time': use_sim_time}],
    )

    gz_sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([FindPackageShare('ros_gz_sim'), 'launch', 'gz_sim.launch.py'])
        ]),
        launch_arguments=[('gz_args', [gazebo_world, ' -r'])],
    )

    spawn_robot = Node(
        package='ros_gz_sim',
        executable='create',
        output='screen',
        arguments=['-topic', 'robot_description', '-name', 'my_robot', '-allow_renaming', 'true'],
    )

    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=['/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock'],
        output='screen',
    )

    joint_state_broadcaster_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['joint_state_broadcaster'],
    )

    diff_drive_controller_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['diff_drive_controller', '--param-file', robot_controllers],
    )

    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='true'),
        gz_sim,
        bridge,
        robot_state_publisher,
        rviz,
        spawn_robot,
        RegisterEventHandler(
            event_handler=OnProcessExit(
                target_action=spawn_robot,
                on_exit=[joint_state_broadcaster_spawner],
            )
        ),
        RegisterEventHandler(
            event_handler=OnProcessExit(
                target_action=joint_state_broadcaster_spawner,
                on_exit=[diff_drive_controller_spawner],
            )
        ),
    ])
