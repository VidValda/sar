from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, PythonExpression, TextSubstitution
from launch_ros.actions import Node

PACKAGE_NAME = "sar_perception"

def generate_launch_description():
    use_realsense = LaunchConfiguration("use_realsense")
    marker_size = LaunchConfiguration("marker_size")
    aruco_dict = LaunchConfiguration("aruco_dict")
    image_topic = LaunchConfiguration("image_topic")
    camera_info_topic = LaunchConfiguration("camera_info_topic")
    marker_mesh_resource = LaunchConfiguration("marker_mesh_resource")
    marker_pose_offset_z = LaunchConfiguration("marker_pose_offset_z")
    image_rotation = LaunchConfiguration("image_rotation")
    publish_map_tf = LaunchConfiguration("publish_map_tf")
    rs_rgb_width = LaunchConfiguration("rs_rgb_width")
    rs_rgb_height = LaunchConfiguration("rs_rgb_height")
    rs_rgb_fps = LaunchConfiguration("rs_rgb_fps")
    publish_debug_image = LaunchConfiguration("publish_debug_image")
    debug_image_rate = LaunchConfiguration("debug_image_rate")

    declare_use_realsense_arg = DeclareLaunchArgument(
        "use_realsense", default_value="false", description="Launch RealSense D435i camera driver"
    )

    declare_marker_size_arg = DeclareLaunchArgument(
        "marker_size", default_value="0.128", description="ArUco marker size in meters"
    )

    declare_aruco_dict_arg = DeclareLaunchArgument(
        "aruco_dict", default_value="DICT_6X6_1000", description="ArUco dictionary to use"
    )

    declare_image_topic_arg = DeclareLaunchArgument(
        "image_topic",
        default_value=PythonExpression([
            "'/camera/color/image_raw' if '", use_realsense, "' == 'true' else '/oak/rgb/color'"
        ]),
        description="Camera image topic",
    )

    declare_camera_info_topic_arg = DeclareLaunchArgument(
        "camera_info_topic",
        default_value="",
        description="CameraInfo topic. Empty derives it from image_topic by replacing the last segment with 'camera_info'.",
    )

    declare_marker_mesh_resource_arg = DeclareLaunchArgument(
        "marker_mesh_resource",
        default_value="",
        description="package:// URI of a mesh to render as the RViz marker. Empty falls back to a green CUBE.",
    )

    declare_marker_pose_offset_z_arg = DeclareLaunchArgument(
        "marker_pose_offset_z",
        default_value="0.0",
        description="Offset (m) along the marker's local Z axis applied to the published pose. Use -marker_size/2 to move from the face to the cube center.",
    )

    declare_image_rotation_arg = DeclareLaunchArgument(
        "image_rotation",
        default_value="0",
        description="Rotate the input image by this many degrees before detection (0/90/180/270). Use 180 if the camera is mounted upside-down. Intrinsics and pose are compensated.",
    )

    declare_publish_map_tf_arg = DeclareLaunchArgument(
        "publish_map_tf",
        default_value="true",
        description="Publish a static identity transform map -> camera_link so /aruco/marker can be rendered in the map frame when running standalone. Set to false when SLAM (or any other source) already provides the map frame.",
    )

    declare_rs_rgb_width_arg = DeclareLaunchArgument(
        "rs_rgb_width", default_value="424", description="RealSense RGB stream width"
    )

    declare_rs_rgb_height_arg = DeclareLaunchArgument(
        "rs_rgb_height", default_value="240", description="RealSense RGB stream height"
    )

    declare_rs_rgb_fps_arg = DeclareLaunchArgument(
        "rs_rgb_fps", default_value="15", description="RealSense RGB stream FPS"
    )

    declare_publish_debug_image_arg = DeclareLaunchArgument(
        "publish_debug_image",
        default_value="false",
        description="Publish the annotated /aruco/image (BEST_EFFORT, throttled to debug_image_rate). Off by default because the raw stream saturates WiFi the moment a remote node (RViz) subscribes. When true, an image_transport republisher is also started to publish /aruco/image/compressed.",
    )

    declare_debug_image_rate_arg = DeclareLaunchArgument(
        "debug_image_rate",
        default_value="5.0",
        description="Max publish rate (Hz) for /aruco/image when publish_debug_image is true.",
    )

    realsense_node = Node(
        package="realsense2_camera",
        executable="realsense2_camera_node",
        name="realsense2_camera",
        parameters=[{
            "enable_color": True,
            "enable_depth": False,
            "enable_infra1": False,
            "enable_infra2": False,
            "enable_gyro": False,
            "enable_accel": False,
            "initial_reset": True,
            "rgb_camera.color_profile": [
                rs_rgb_width, TextSubstitution(text="x"),
                rs_rgb_height, TextSubstitution(text="x"),
                rs_rgb_fps,
            ],
            # The realsense driver's default QoS for image streams is
            # RELIABLE + TRANSIENT_LOCAL — wrong for sensor data and lethal over
            # WiFi: every dropped packet triggers a reliable retry, and every
            # new subscriber gets buffered frames re-shipped. Override to the
            # standard sensor_data profile (BEST_EFFORT + VOLATILE) so drops
            # are silent and late joiners only get fresh frames.
            "qos_overrides./camera/realsense2_camera/color/image_raw.publisher.reliability": "best_effort",
            "qos_overrides./camera/realsense2_camera/color/image_raw.publisher.durability": "volatile",
            "qos_overrides./camera/realsense2_camera/color/camera_info.publisher.reliability": "best_effort",
            "qos_overrides./camera/realsense2_camera/color/camera_info.publisher.durability": "volatile",
        }],
        output="screen",
        condition=IfCondition(use_realsense),
    )

    map_to_camera_static_tf = Node(
        package="tf2_ros",
        executable="static_transform_publisher",
        name="map_to_camera_link_static_tf",
        arguments=[
            "--frame-id", "base_link",
            "--child-frame-id", "camera_link",
            "--x", "0", "--y", "0", "--z", "0",
            "--roll", "0", "--pitch", "0", "--yaw", "0",
        ],
        condition=IfCondition(publish_map_tf),
    )

    aruco_detector = Node(
        package=PACKAGE_NAME,
        executable="aruco_detector",
        name="aruco_detector",
        parameters=[
            {"marker_size": marker_size},
            {"aruco_dict": aruco_dict},
            {"image_topic": image_topic},
            {"camera_info_topic": camera_info_topic},
            {"marker_mesh_resource": marker_mesh_resource},
            {"marker_pose_offset_z": marker_pose_offset_z},
            {"image_rotation": image_rotation},
            {"publish_debug_image": publish_debug_image},
            {"debug_image_rate": debug_image_rate},
        ],
        output="screen",
    )

    # Publishes /aruco/image/compressed (JPEG) from the raw /aruco/image stream.
    # Only started when publish_debug_image is true — gives tools that handle
    # image_transport (rqt_image_view, foxglove) a ~30x smaller stream to pull
    # over WiFi. RViz's stock Image display reads /aruco/image directly.
    aruco_image_republisher = Node(
        package="image_transport",
        executable="republish",
        name="aruco_image_republisher",
        arguments=["raw", "compressed"],
        remappings=[
            ("in", "/aruco/image"),
            ("out", "/aruco/image"),
        ],
        condition=IfCondition(publish_debug_image),
        output="screen",
    )

    return LaunchDescription(
        [
            declare_use_realsense_arg,
            declare_marker_size_arg,
            declare_aruco_dict_arg,
            declare_image_topic_arg,
            declare_camera_info_topic_arg,
            declare_marker_mesh_resource_arg,
            declare_marker_pose_offset_z_arg,
            declare_image_rotation_arg,
            declare_publish_map_tf_arg,
            declare_rs_rgb_width_arg,
            declare_rs_rgb_height_arg,
            declare_rs_rgb_fps_arg,
            declare_publish_debug_image_arg,
            declare_debug_image_rate_arg,
            realsense_node,
            map_to_camera_static_tf,
            aruco_detector,
            aruco_image_republisher,
        ]
    )
