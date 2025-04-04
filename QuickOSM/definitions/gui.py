"""Definitions for GUI concepts."""

from enum import Enum, unique

__copyright__ = 'Copyright 2021, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'


@unique
class Panels(Enum):
    """Name of panels in the GUI."""
    MapPreset = 'MapPreset'
    QuickQuery = 'QuickQuery'
    Query = 'Query'
    File = 'File'
    Configuration = 'Configuration'
