cmake_minimum_required(VERSION 3.0.2)
project(android_core)

find_package(catkin REQUIRED rosjava_build_tools)

catkin_android_setup(assembleRelease uploadArchives)

catkin_package()

install(
  DIRECTORY ${CATKIN_DEVEL_PREFIX}/${CATKIN_GLOBAL_MAVEN_DESTINATION}/org/ros/android_core/
  DESTINATION ${CATKIN_GLOBAL_MAVEN_DESTINATION}/org/ros/android_core
)
