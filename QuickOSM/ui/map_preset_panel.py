"""Panel OSM map preset class."""
import datetime
import json
import logging
import os

from functools import partial
from os.path import join

from qgis.core import QgsApplication
from qgis.PyQt.QtCore import QSize
from qgis.PyQt.QtGui import QIcon, QPixmap
from qgis.PyQt.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidgetItem,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
)

from QuickOSM.core.process import process_query
from QuickOSM.core.utilities.json_encoder import as_enum
from QuickOSM.core.utilities.query_saved import QueryManagement
from QuickOSM.core.utilities.tools import query_bookmark
from QuickOSM.definitions.gui import Panels
from QuickOSM.definitions.osm import Osm_Layers
from QuickOSM.qgis_plugin_tools.tools.i18n import tr
from QuickOSM.qgis_plugin_tools.tools.resources import resources_path
from QuickOSM.ui.base_overpass_panel import BaseOverpassPanel
from QuickOSM.ui.edit_bookmark import EditBookmark

__copyright__ = 'Copyright 2021, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'

LOGGER = logging.getLogger('QuickOSM')


class MapPresetPanel(BaseOverpassPanel):
    """Implementation of the map preset panel."""

    def __init__(self, dialog: QDialog):
        """Constructor"""
        super().__init__(dialog)
        self.panel = Panels.MapPreset

    def setup_panel(self):
        super().setup_panel()
        """Setup the UI for the QuickQuery."""

        # Query type
        self.dialog.combo_query_type_mp.addItem(tr('In'), 'in')
        self.dialog.combo_query_type_mp.addItem(tr('Around'), 'around')
        self.dialog.combo_query_type_mp.addItem(tr('Canvas Extent'), 'canvas')
        self.dialog.combo_query_type_mp.addItem(tr('Layer Extent'), 'layer')
        self.dialog.combo_query_type_mp.addItem(tr('Not Spatial'), 'attributes')

        self.dialog.combo_query_type_mp.currentIndexChanged.connect(
            self.query_type_updated)
        self.dialog.combo_extent_layer_mp.layerChanged.connect(self.query_type_updated)

        self.setup_default_preset()
        self.dialog.list_default_mp.itemSelectionChanged.connect(
            self.dialog.list_bookmark_mp.clearSelection)
        self.dialog.list_bookmark_mp.itemSelectionChanged.connect(
            self.dialog.list_default_mp.clearSelection)

        self.query_type_updated()
        self.init_nominatim_autofill()

        self.update_bookmark_view()

    def setup_default_preset(self):
        """Setup the display of presets"""
        preset_folder = resources_path('map_preset')
        files = os.listdir(preset_folder)
        files_json = filter(lambda file_ext: file_ext[-5:] == '.json', files)

        for file in files_json:
            file_path = join(preset_folder, file)
            with open(file_path, encoding='utf8') as json_file:
                data = json.load(json_file, object_hook=as_enum)

            item = QListWidgetItem(self.dialog.list_default_mp)
            self.dialog.list_default_mp.addItem(item)

            widget = QFrame()
            widget.setFrameStyle(QFrame.StyledPanel)
            widget.setStyleSheet('QFrame { margin: 3px; }')
            widget.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            hbox = QHBoxLayout()
            vbox = QVBoxLayout()
            picture = QLabel()
            icon = QPixmap((resources_path('icons', 'QuickOSM.svg')))
            icon.scaled(QSize(100, 100))
            picture.setPixmap(icon)
            hbox.addWidget(picture)
            title = QLabel(data['file_name'])
            title.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            title.setStyleSheet('font: bold 20px; ')
            vbox.addWidget(title)
            for label in data['description']:
                if not label:
                    label = tr('No description')
                real_label = QLabel(label)
                real_label.setWordWrap(True)
                vbox.addWidget(real_label)
            hbox.addItem(vbox)
            widget.setLayout(hbox)

            item.setSizeHint(widget.minimumSizeHint())
            self.dialog.list_default_mp.setItemWidget(item, widget)

    def query_type_updated(self):
        """Update the ui when the query type is modified."""
        self._core_query_type_updated(
            self.dialog.combo_query_type_mp,
            self.dialog.stacked_query_type_mp,
            self.dialog.spin_place_mp,
            self.dialog.checkbox_selection_mp)

    def update_bookmark_view(self):
        """Update the bookmarks displayed."""
        bookmark_folder = query_bookmark()
        files = os.listdir(bookmark_folder)
        files_json = filter(lambda file_ext: file_ext[-5:] == '.json', files)

        self.dialog.list_bookmark_mp.clear()

        for file in files_json:
            file_path = join(bookmark_folder, file)
            with open(file_path, encoding='utf8') as json_file:
                data = json.load(json_file, object_hook=as_enum)
            name = data['file_name']

            item = QListWidgetItem(self.dialog.list_bookmark_mp)
            self.dialog.list_bookmark_mp.addItem(item)

            bookmark = QFrame()
            bookmark.setFrameStyle(QFrame.StyledPanel)
            bookmark.setStyleSheet('QFrame { margin: 3px; }')
            bookmark.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            hbox = QHBoxLayout()
            vbox = QVBoxLayout()
            label_name = QLabel(name)
            label_name.setStyleSheet('font-weight: bold;')
            label_name.setWordWrap(True)
            vbox.addWidget(label_name)
            for label in data['description']:
                if not label:
                    label = tr('No description')
                real_label = QLabel(label)
                real_label.setWordWrap(True)
                vbox.addWidget(real_label)
            hbox.addItem(vbox)
            button_run = QPushButton()
            button_edit = QPushButton()
            button_remove = QPushButton()
            button_run.setIcon(QIcon(QgsApplication.iconPath("mActionStart.svg")))
            button_edit.setIcon(QIcon(QgsApplication.iconPath("mActionToggleEditing.svg")))
            button_remove.setIcon(QIcon(QgsApplication.iconPath('symbologyRemove.svg')))
            button_run.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            button_edit.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            button_remove.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            button_run.setToolTip(tr('Run the queries in the bookmark'))
            button_edit.setToolTip(tr('Edit the bookmark'))
            button_remove.setToolTip(tr('Delete the bookmark'))
            hbox.addWidget(button_run)
            hbox.addWidget(button_edit)
            hbox.addWidget(button_remove)
            bookmark.setLayout(hbox)

            # Actions on click
            remove = partial(self.remove_bookmark, item, name)
            button_remove.clicked.connect(remove)
            edit = partial(self.edit_bookmark, data)
            button_edit.clicked.connect(edit)
            run = partial(self.run_saved_query, data)
            button_run.clicked.connect(run)

            item.setSizeHint(bookmark.minimumSizeHint())
            self.dialog.list_bookmark_mp.setItemWidget(item, bookmark)

    def edit_bookmark(self, data: dict):
        """Open a dialog to edit the bookmark"""
        edit_dialog = EditBookmark(self.dialog, data)
        edit_dialog.show()
        self.update_bookmark_view()

    def remove_bookmark(self, item: QListWidgetItem, name: str):
        """Remove a bookmark."""
        index = self.dialog.list_bookmark_mp.row(item)
        self.dialog.list_bookmark_mp.takeItem(index)

        q_manage = QueryManagement()
        q_manage.remove_bookmark(name)

    def _run_saved_query(self, data: dict):
        """Run a saved query(ies)."""
        for k, query in enumerate(data['query']):
            if data['output_directory'][k]:
                time_str = str(datetime.datetime.now()).replace(' ', '_').replace(':', '-').split('.')[0]
                name = time_str + '_' + data['query_layer_name'][k]
            else:
                name = data['query_layer_name'][k]
            bookmark_folder = query_bookmark()
            files = os.listdir(bookmark_folder)
            files_qml = filter(lambda file_ext: file_ext[-4:] == '.qml', files)
            file_name = join(data['file_name'] + '_' + data['query_name'][k])
            files_qml = filter(lambda file_ext: file_ext.startswith(file_name), files_qml)
            if list(files_qml):
                LOGGER.debug('files: {}'.format(files_qml))
                file_name = join(bookmark_folder, data['file_name'] + '_' + data['query_name'][k] + '_{}.qml')
                config = {}
                for osm_type in Osm_Layers:
                    config[osm_type] = {
                        'namelayer': name,
                        'style': file_name.format(osm_type)
                    }
            else:
                config = None

            num_layers = process_query(
                dialog=self.dialog,
                query=query,
                description=data['description'],
                layer_name=name,
                white_list_values=data['white_list_column'][k],
                area=data['area'][k],
                bbox=data['bbox'][k],
                output_geometry_types=data['output_geom_type'][k],
                output_format=data['output_format'][k],
                output_dir=data['output_directory'][k],
                config_outputs=config
            )
            self.end_query(num_layers)
