"""Dialog that edit a preset"""
import logging

from qgis.core import QgsCoordinateReferenceSystem
from qgis.gui import QgsExtentWidget, QgsFileWidget
from qgis.PyQt.QtCore import QPoint, Qt
from qgis.PyQt.QtWidgets import (
    QDialog,
    QInputDialog,
    QListWidgetItem,
    QMenu,
    QMessageBox,
)

from QuickOSM.core.utilities.query_saved import QueryManagement
from QuickOSM.core.utilities.tools import query_preset
from QuickOSM.definitions.format import Format
from QuickOSM.definitions.gui import Panels
from QuickOSM.definitions.osm import LayerType
from QuickOSM.qgis_plugin_tools.tools.i18n import tr
from QuickOSM.qgis_plugin_tools.tools.resources import load_ui
from QuickOSM.ui.custom_table import TableKeyValue

__copyright__ = 'Copyright 2021, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'

Qml_Format = tr(
    'To associate a qml style file for each layer, you must add'
    ' the qml file(s) in the folder {}\\\'name of the preset\'\\ '
    'with the name in a peculiar format : '
    '\'name of the preset\'_\'name of the query\'_\'layer\'.')

FORM_CLASS = load_ui('edit_preset.ui')
LOGGER = logging.getLogger('QuickOSM')


class EditPreset(QDialog, FORM_CLASS, TableKeyValue):
    """Dialog that edit a preset"""

    def __init__(self, parent=None, data_preset: dict = None):
        """Constructor."""
        QDialog.__init__(self, parent)
        self.setupUi(self)
        self.dialog = parent
        self.panel = Panels.MapPreset
        self.folder = query_preset()
        TableKeyValue.__init__(self, self.table_keys_values_eb, self.combo_preset_eb)
        self.setup_preset()
        self.setup_table()

        self.previous_name = data_preset['file_name']
        self.current_query = 0
        self.nb_queries = len(data_preset['query'])

        for k in range(self.nb_queries):
            self.list_queries.addItem(data_preset['query_name'][k])

        self.button_add.clicked.connect(self.add_query)
        self.list_queries.currentRowChanged.connect(self.change_query)
        self.list_queries.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_queries.customContextMenuRequested.connect(self.item_context)

        self.bbox = QgsExtentWidget()
        self.bbox.setMapCanvas(parent.iface.mapCanvas())
        self.bbox_layout.addWidget(self.bbox)
        self.crs = QgsCoordinateReferenceSystem('EPSG:4326')

        self.combo_output_format.addItem(
            Format.GeoPackage.value.label, Format.GeoPackage)
        self.combo_output_format.addItem(
            Format.GeoJSON.value.label, Format.GeoJSON)
        self.combo_output_format.addItem(
            Format.Shapefile.value.label, Format.Shapefile)
        self.combo_output_format.addItem(
            Format.Kml.value.label, Format.Kml)

        self.output_directory.lineEdit().setPlaceholderText(
            tr('Save to temporary file'))
        self.output_directory.setStorageMode(
            QgsFileWidget.GetDirectory)

        self.data = data_preset.copy()
        if self.data:
            self.preset_name.setText(self.data['file_name'])
            self.description.setPlainText('\\n'.join(self.data['description']))

            if self.data['advanced']:
                self.radio_advanced.setChecked(True)
                self.change_type_preset()
            self.data_filling_form()

        self.disable_enable_format()
        self.update_qml_format()

        self.preset_name.textChanged.connect(self.update_qml_format)
        self.radio_advanced.toggled.connect(self.change_type_preset)
        self.output_directory.lineEdit().textChanged.connect(self.disable_enable_format)
        self.button_validate.clicked.connect(self.validate)
        self.button_cancel.clicked.connect(self.close)

    def item_context(self, pos: QPoint):
        """Set context submenu to delete item in the list."""
        item = self.list_queries.mapToGlobal(pos)
        submenu = QMenu()
        rename_action = submenu.addAction(tr('Rename'))
        delete_action = submenu.addAction(tr('Delete'))
        right_click_item = submenu.exec_(item)
        if right_click_item and right_click_item == delete_action:
            index = self.list_queries.indexAt(pos).row()
            self.verification_delete_query(index)
        if right_click_item and right_click_item == rename_action:
            query = self.list_queries.itemAt(pos)
            self.rename_query(query)

    def disable_enable_format(self):
        """Enable only if the directory is set."""
        boolean = not self.output_directory.lineEdit().isNull()
        self.combo_output_format.setEnabled(boolean)

    def update_qml_format(self):
        """Update the explanation of the qml file name format."""
        file_name = self.preset_name.text()
        query_name = self.list_queries.item(self.current_query).text()
        name_file = file_name + '_' + query_name + '_points.qml'

        self.qml_format.setText(Qml_Format.format(self.folder) + tr('\nFor example: ') + name_file)

    def data_filling_form(self, num_query: int = 0):
        """Writing the form with data from preset"""

        self.layer_name.setText(self.data['query_layer_name'][num_query])
        self.query.setPlainText(self.data['query'][num_query])
        keys = self.data['keys'][num_query]
        values = self.data['values'][num_query]
        type_multi_request = self.data['type_multi_request'][num_query]
        self.fill_table(keys, values, type_multi_request)

        self.area.setText(self.data['area'][num_query])
        if self.data['bbox'][num_query]:
            self.bbox.setOutputExtentFromUser(self.data['bbox'][num_query], self.crs)
        else:
            self.bbox.clear()

        if LayerType.Points in self.data['output_geom_type'][num_query]:
            self.checkbox_points.setChecked(True)
        else:
            self.checkbox_points.setChecked(False)
        if LayerType.Lines in self.data['output_geom_type'][num_query]:
            self.checkbox_lines.setChecked(True)
        else:
            self.checkbox_lines.setChecked(False)
        if LayerType.Multilinestrings in self.data['output_geom_type'][num_query]:
            self.checkbox_multilinestrings.setChecked(True)
        else:
            self.checkbox_multilinestrings.setChecked(False)
        if LayerType.Multipolygons in self.data['output_geom_type'][num_query]:
            self.checkbox_multipolygons.setChecked(True)
        else:
            self.checkbox_multipolygons.setChecked(False)

        if self.data['white_list_column'][num_query]['points']:
            self.white_points.setText(self.data['white_list_column'][num_query]['points'])
        else:
            self.white_points.setText('')
        if self.data['white_list_column'][num_query]['lines']:
            self.white_lines.setText(self.data['white_list_column'][num_query]['lines'])
        else:
            self.white_lines.setText('')
        if self.data['white_list_column'][num_query]['multilinestrings']:
            self.white_multilinestrings.setText(self.data['white_list_column'][num_query]['multilinestrings'])
        else:
            self.white_multilinestrings.setText('')
        if self.data['white_list_column'][num_query]['multipolygons']:
            self.white_multipolygons.setText(self.data['white_list_column'][num_query]['multipolygons'])
        else:
            self.white_multipolygons.setText('')

        index = self.combo_output_format.findData(self.data['output_format'][num_query])
        self.combo_output_format.setCurrentIndex(index)

        self.output_directory.setFilePath(self.data['output_directory'][num_query])

    def change_type_preset(self):
        """Update the form according the preset type."""
        if self.radio_advanced.isChecked():
            self.stacked_parameters_preset.setCurrentWidget(self.advanced_parameters)
        else:
            self.stacked_parameters_preset.setCurrentWidget(self.basic_parameters)

    def change_query(self):
        """Display the selected query in the view."""
        self.gather_parameters(self.current_query)
        self.current_query = self.list_queries.currentRow()
        self.data_filling_form(self.current_query)
        self.update_qml_format()

    def add_query(self):
        """Add a query in the preset"""
        q_manage = QueryManagement()
        self.data = q_manage.add_empty_query_in_preset(self.data)

        new_query = QListWidgetItem(tr('Query') + str(self.nb_queries + 1))
        self.list_queries.addItem(new_query)
        self.nb_queries += 1

        self.list_queries.setCurrentItem(new_query)

    def verification_delete_query(self, row: int):
        """Delete a query in the preset"""
        name = self.list_queries.item(row).text()
        validate_delete = QMessageBox(
            QMessageBox.Warning, tr('Confirm query deletion'),
            tr('Are you sure you want to delete the query \'{}\'?'.format(name)),
            QMessageBox.Yes | QMessageBox.Cancel, self
        )
        ok = validate_delete.exec()

        if ok == QMessageBox.Yes:
            self.delete_query(row)

    def delete_query(self, row: int):
        """Delete a query in the preset"""
        self.nb_queries -= 1

        self.list_queries.takeItem(row)

        q_manage = QueryManagement()
        self.data = q_manage.remove_query_in_preset(self.data, row)

        for k in range(row, self.nb_queries):
            self.list_queries.item(k).setText(tr('Query') + str(k + 1))

        self.current_query = self.list_queries.currentRow()

    def rename_query(self, query: QListWidgetItem):
        """Rename a query in the preset"""
        input_dialog = QInputDialog(self)
        new_name = input_dialog.getText(
            self, tr("Rename the query"),
            tr("New name:"), text=query.text())
        if new_name[1] and new_name[0]:
            query.setText(new_name[0].replace(' ', '_'))
            self.update_qml_format()

    def show_extent_canvas(self):
        """Show the extent in the canvas"""
        if self.data['bbox'][self.current_query]:
            self.canvas.setMapTool(self.show_extent_tool)
            self.show_extent_tool.show_extent(self.data['bbox'][self.current_query])

            self.setVisible(False)
            self.dialog.setVisible(False)

    def end_show_extent(self):
        """End the show of the extent."""
        self.canvas.unsetMapTool(self.show_extent_tool)

        self.setVisible(True)
        self.dialog.setVisible(True)

    def gather_general_parameters(self):
        """Save the general parameters."""
        self.data['file_name'] = self.preset_name.text().replace(' ', '_')
        description = self.description.toPlainText().split('\\n')
        self.data['description'] = description
        self.data['advanced'] = self.radio_advanced.isChecked()
        list_name_queries = [
            self.list_queries.item(k).text().replace(' ', '_') for k in range(self.list_queries.count())
        ]
        self.data['query_name'] = list_name_queries

    def gather_parameters(self, num_query: int = 0):
        """Save the parameters."""
        self.data['query_layer_name'][num_query] = self.layer_name.text()
        self.data['query'][num_query] = self.query.toPlainText()
        properties = self.gather_couple({})
        self.data['keys'][num_query] = properties['key']
        self.data['values'][num_query] = properties['value']
        self.data['type_multi_request'][num_query] = properties['type_multi_request']
        self.data['area'][num_query] = self.area.text()
        if self.bbox.outputExtent():
            self.bbox.setOutputCrs(self.crs)
            self.data['bbox'][num_query] = self.bbox.outputExtent()
        else:
            self.data['bbox'][num_query] = ''

        output_geom = []
        if self.checkbox_points.isChecked():
            output_geom.append(LayerType.Points)
        if self.checkbox_lines.isChecked():
            output_geom.append(LayerType.Lines)
        if self.checkbox_multilinestrings.isChecked():
            output_geom.append(LayerType.Multilinestrings)
        if self.checkbox_multipolygons.isChecked():
            output_geom.append(LayerType.Multipolygons)
        self.data['output_geom_type'][num_query] = output_geom

        if self.white_points.text():
            white_list = {'points': self.white_points.text()}
        else:
            white_list = {'points': None}
        if self.white_lines.text():
            white_list['lines'] = self.white_lines.text()
        else:
            white_list['lines'] = None
        if self.white_multilinestrings.text():
            white_list['multilinestrings'] = self.white_multilinestrings.text()
        else:
            white_list['multilinestrings'] = None
        if self.white_multipolygons.text():
            white_list['multipolygons'] = self.white_multipolygons.text()
        else:
            white_list['multipolygons'] = None
        self.data['white_list_column'][num_query] = white_list

        self.data['output_format'][num_query] = self.combo_output_format.currentData()
        self.data['output_directory'][num_query] = self.output_directory.filePath()

    def validate(self):
        """Update the preset"""
        self.gather_parameters(self.current_query)
        self.gather_general_parameters()

        q_manage = QueryManagement()
        if self.previous_name != self.data['file_name']:
            q_manage.rename_preset(self.previous_name, self.data['file_name'], self.data)
        else:
            q_manage.update_preset(self.data)

        self.dialog.external_panels[Panels.MapPreset].update_personal_preset_view()
        self.close()
