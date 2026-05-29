#!/usr/bin/env sh

# Strip any system ROS installation (e.g. /opt/ros/jazzy) from the
# environment so the pixi-provided Humble libraries always win.
_strip_ros_path() {
  echo "$1" | tr ':' '\n' | grep -v '^/opt/ros/' | tr '\n' ':' | sed 's/:$//'
}

LD_LIBRARY_PATH=$(_strip_ros_path "$LD_LIBRARY_PATH")
CMAKE_PREFIX_PATH=$(_strip_ros_path "$CMAKE_PREFIX_PATH")
AMENT_PREFIX_PATH=$(_strip_ros_path "$AMENT_PREFIX_PATH")
PYTHONPATH=$(_strip_ros_path "$PYTHONPATH")
PATH=$(echo "$PATH" | tr ':' '\n' | grep -v '^/opt/ros/' | tr '\n' ':' | sed 's/:$//')
LD_LIBRARY_PATH="${CONDA_PREFIX}/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export LD_LIBRARY_PATH CMAKE_PREFIX_PATH AMENT_PREFIX_PATH PYTHONPATH PATH

# Source ROS workspace setup only when it exists.
if [ -f "install/setup.sh" ]; then
  . "install/setup.sh"
fi
