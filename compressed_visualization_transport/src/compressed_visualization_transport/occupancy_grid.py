# Copyright (C) 2011 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License. You may obtain a copy of
# the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations under
# the License.

"""Draws an occupancy grid into a PIL image."""

__author__ = 'moesenle@google.com (Lorenz Moesenlechner)'
import io
from PIL import Image

from compressed_visualization_transport import compressed_bitmap

import nav_msgs.msg as nav_msgs
import compressed_visualization_transport_msgs.msg as compressed_visualization_transport_msgs


_DEFAULT_COLOR_UNKNOWN = 128
_DEFAULT_COLOR_OCCUPIED = 0
_DEFAULT_COLOR_FREE = 1


class ColorConfiguration(object):
  """Color specification to use when converting from an occupancy grid
  to a bitmap."""

  def __init__(self, color_occupied=None, color_free=None, color_unknown=None):
    if color_occupied is None:
      color_occupied = GrayColor(_DEFAULT_COLOR_OCCUPIED)
    self.color_occupied = color_occupied
    if color_free is None:
      color_free = GrayColor(_DEFAULT_COLOR_FREE)
    self.color_free = color_free
    if color_unknown is None:
      color_unknown = GrayColor(_DEFAULT_COLOR_UNKNOWN)
    self.color_unknown = color_unknown
    if not (color_occupied.format == color_free.format == color_unknown.format):
      raise Exception('All colors need to have the same format.')
    self.format = color_occupied.format


class GrayColor(object):

  def __init__(self, value):
    self.value = value
    self.byte_value = chr(value)
    self.format = 'L'


class RGBAColor(object):

  def __init__(self, red, green, blue, alpha):
    self.value = alpha << 24 | red << 16 | green << 8 | blue
    self.byte_value = self._encode()
    self.format = 'RGBA'

  def _encode(self):
    bytes = bytearray(4)
    for i in range(4):
      bytes[i] = (self.value >> (i * 8) & 0xff)
    return bytes


def _occupancy_to_bytes(data, color_configuration):
  for value in data:
    if value == -1:
      yield color_configuration.color_unknown.byte_value
    elif value == 0:
      yield color_configuration.color_free.byte_value
    else:
      yield color_configuration.color_occupied.byte_value


def _bytes_to_occupancy(data, color_configuration):
  for value in data:
    if value == color_configuration.color_unknown.value:
      yield -1
    elif value == color_configuration.color_free.value:
      yield 0
    else:
      yield 100


def _calculate_scaled_size(size, old_resolution, new_resolution):
  width, height = size
  scaling_factor = old_resolution / new_resolution
  return (int(width * scaling_factor),
          int(height * scaling_factor))


def _make_scaled_map_metadata(metadata, resolution):
  width, height = _calculate_scaled_size(
    (metadata.width, metadata.height),
    metadata.resolution, resolution)
  return nav_msgs.MapMetaData(
    map_load_time=metadata.map_load_time,
    resolution=resolution,
    width=width, height=height,
    origin=metadata.origin)
    

def calculate_resolution(goal_size, current_size, current_resolution):
  goal_width, goal_height = goal_size
  current_width, current_height = current_size
  # always use the smallest possible resolution
  width_resolution = (
    float(current_width) / float(goal_width) * current_resolution)
  height_resolution = (
    float(current_height) / float(goal_height) * current_resolution)
  return max(width_resolution, height_resolution)


def occupancy_grid_to_image(occupancy_grid, color_configuration=None):
  if color_configuration is None:
    color_configuration = ColorConfiguration()
  data_stream = io.BytesIO()
  for value in _occupancy_to_bytes(occupancy_grid.data, color_configuration):
    data_stream.write(value)
  return Image.fromstring(
      color_configuration.format,
      (occupancy_grid.info.width, occupancy_grid.info.height),
      data_stream.getvalue())


def image_to_occupancy_grid_data(image, color_configuration=None):
  if color_configuration is None:
    color_configuration = ColorConfiguration()
  color_configuration = ColorConfiguration()  
  return _bytes_to_occupancy(
      image.getdata(), color_configuration)


def scale_occupancy_grid(occupancy_grid, resolution, color_configuration=None):
  """Scales an occupancy grid message.

  Takes an occupancy grid message, scales it to have the new size and
  returns the scaled grid.

  Parameters:
    occupancy_grid: the occupancy grid message to scale
    resolution: the resolution the scaled occupancy grid should have
  """
  image = occupancy_grid_to_image(occupancy_grid, color_configuration)
  new_size = _calculate_scaled_size(
    (occupancy_grid.info.width, occupancy_grid.info.height),
    occupancy_grid.info.resolution, resolution)
  resized_image = image.resize(new_size)
  result = nav_msgs.OccupancyGrid()
  result.header = occupancy_grid.header
  result.info = _make_scaled_map_metadata(occupancy_grid.info, resolution)
  result.data = list(image_to_occupancy_grid_data(resized_image))
  return result


def compress_occupancy_grid(occupancy_grid, resolution, format, color_configuration=None):
  """Scales and compresses an occupancy grid message.

  Takes an occupancy grid message, scales it and creates a compressed
  representation with the specified format.

  Parameters:
    occupancy_grid: the occupancy grid message
    resolution: the resolution of the compressed occupancy grid
    format: the format of the compressed data (e.g. png)
  """
  image = occupancy_grid_to_image(occupancy_grid, color_configuration)
  new_size = _calculate_scaled_size(
    (occupancy_grid.info.width, occupancy_grid.info.height),
    occupancy_grid.info.resolution, resolution)
  resized_image = image.resize(new_size)
  result = compressed_visualization_transport_msgs.CompressedBitmap()
  result.header = occupancy_grid.header
  result.origin = occupancy_grid.info.origin
  result.resolution_x = resolution
  result.resolution_y = resolution
  compressed_bitmap.fill_compressed_bitmap(resized_image, format, result)
  return result