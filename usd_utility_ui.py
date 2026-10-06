"""USD Utility Tool: a PySide window that docks to Maya's main window.

Run from the Maya Script Editor (Python tab):

    import sys
    sys.path.append("/Users/rodney/Workspace/USDUtil")
    import usd_utility_ui
    usd_utility_ui.show()
"""
import importlib

try:  # Maya 2025+ ships PySide6; older versions ship PySide2
    from PySide6 import QtCore, QtWidgets
    from shiboken6 import wrapInstance
except ImportError:
    from PySide2 import QtCore, QtWidgets
    from shiboken2 import wrapInstance

from maya import cmds
import maya.OpenMayaUI as omui

import usd_ops

importlib.reload(usd_ops)  # pick up edits without restarting Maya

_window = None


def _maya_main_window():
    return wrapInstance(int(omui.MQtUtil.mainWindow()), QtWidgets.QWidget)


class UsdUtilityWindow(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent or _maya_main_window())
        self.setWindowTitle("USD Utility Tool")
        self.setWindowFlag(QtCore.Qt.Tool)
        self.setMinimumWidth(420)
        self._results = []  # prims currently listed in the results panel
        self._build_ui()
        self._refresh_stages()

    # ------------------------------------------------------------ UI
    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)

        # -- Load
        load_box = QtWidgets.QGroupBox("1. Load USD")
        load_l = QtWidgets.QGridLayout(load_box)
        self.path_edit = QtWidgets.QLineEdit()
        self.path_edit.setPlaceholderText("Path to .usd / .usda / .usdc / .usdz")
        browse = QtWidgets.QPushButton("Browse...")
        browse.clicked.connect(self._browse)
        load_btn = QtWidgets.QPushButton("Load into Maya")
        load_btn.clicked.connect(self._load)
        self.stage_combo = QtWidgets.QComboBox()
        self.stage_combo.currentIndexChanged.connect(self._refresh_materials)
        refresh = QtWidgets.QPushButton("Refresh")
        refresh.clicked.connect(self._refresh_stages)
        load_l.addWidget(self.path_edit, 0, 0)
        load_l.addWidget(browse, 0, 1)
        load_l.addWidget(load_btn, 1, 0, 1, 2)
        load_l.addWidget(QtWidgets.QLabel("Active stage:"), 2, 0)
        load_l.addWidget(self.stage_combo, 3, 0)
        load_l.addWidget(refresh, 3, 1)
        layout.addWidget(load_box)

        # -- Find
        find_box = QtWidgets.QGroupBox("2. Find prims")
        find_l = QtWidgets.QGridLayout(find_box)
        self.name_edit = QtWidgets.QLineEdit()
        self.name_edit.setPlaceholderText("name, e.g. chair or *Chair*")
        self.name_edit.returnPressed.connect(self._select_by_name)
        name_btn = QtWidgets.QPushButton("Select by name")
        name_btn.clicked.connect(self._select_by_name)
        self.mat_combo = QtWidgets.QComboBox()
        mat_btn = QtWidgets.QPushButton("Select by material")
        mat_btn.clicked.connect(self._select_by_material)
        self.kind_combo = QtWidgets.QComboBox()
        kind_btn = QtWidgets.QPushButton("Select by kind")
        kind_btn.clicked.connect(self._select_by_kind)
        invis_btn = QtWidgets.QPushButton("Select invisible prims")
        invis_btn.clicked.connect(self._select_invisible)
        find_l.addWidget(self.name_edit, 0, 0)
        find_l.addWidget(name_btn, 0, 1)
        find_l.addWidget(self.mat_combo, 1, 0)
        find_l.addWidget(mat_btn, 1, 1)
        find_l.addWidget(self.kind_combo, 2, 0)
        find_l.addWidget(kind_btn, 2, 1)
        find_l.addWidget(invis_btn, 3, 0, 1, 2)
        layout.addWidget(find_box)

        # -- Act on selection
        act_box = QtWidgets.QGroupBox("3. Act on selected prims")
        act_l = QtWidgets.QHBoxLayout(act_box)
        unload_btn = QtWidgets.QPushButton("Unload payloads")
        unload_btn.clicked.connect(self._unload)
        load_sel_btn = QtWidgets.QPushButton("Load payloads")
        load_sel_btn.clicked.connect(self._load_selected)
        vis_btn = QtWidgets.QPushButton("Make visible")
        vis_btn.clicked.connect(self._make_visible)
        for b in (unload_btn, load_sel_btn, vis_btn):
            act_l.addWidget(b)
        layout.addWidget(act_box)

        # -- Results
        res_box = QtWidgets.QGroupBox("Results (click to select)")
        res_l = QtWidgets.QVBoxLayout(res_box)
        self.result_list = QtWidgets.QListWidget()
        self.result_list.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.result_list.itemSelectionChanged.connect(self._select_from_list)
        res_l.addWidget(self.result_list)
        layout.addWidget(res_box)

        self.status = QtWidgets.QLabel("Load a USD file to begin.")
        layout.addWidget(self.status)

    # ------------------------------------------------------------ helpers
    def _proxy(self):
        return self.stage_combo.currentText() or None

    def _stage(self):
        proxy = self._proxy()
        if not proxy:
            self.status.setText("No USD stage. Load a file first.")
            return None
        return usd_ops.get_stage(proxy)

    def _show_results(self, prims, label):
        proxy = self._proxy()
        self._results = prims
        self.result_list.blockSignals(True)
        self.result_list.clear()
        for p in prims:
            self.result_list.addItem(str(p.GetPath()))
        self.result_list.blockSignals(False)
        usd_ops.select_prims(proxy, prims)
        self.status.setText("{}: {} prim(s)".format(label, len(prims)))

    def _target_prims(self):
        """Prims selected in Maya; falls back to the results list selection."""
        prims = usd_ops.selected_prims()
        if not prims:
            self.status.setText("Select USD prims in the Outliner or viewport first.")
        return prims

    # ------------------------------------------------------------ slots
    def _browse(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Choose USD file", "", "USD files (*.usd *.usda *.usdc *.usdz)")
        if path:
            self.path_edit.setText(path)

    def _load(self):
        path = self.path_edit.text().strip()
        if not path:
            self.status.setText("Choose a USD file first.")
            return
        try:
            shape = usd_ops.load_usd_file(path)
        except Exception as exc:  # surface errors in the UI, not just the log
            self.status.setText("Load failed: {}".format(exc))
            raise
        self._refresh_stages(select=shape)
        self.status.setText("Loaded {}".format(path))

    def _refresh_stages(self, select=None):
        self.stage_combo.blockSignals(True)
        self.stage_combo.clear()
        self.stage_combo.addItems(usd_ops.list_proxy_shapes())
        if select:
            self.stage_combo.setCurrentText(select)
        self.stage_combo.blockSignals(False)
        self._refresh_materials()

    def _refresh_materials(self):
        self.mat_combo.clear()
        self.kind_combo.clear()
        stage = self._stage() if self._proxy() else None
        if stage:
            for name, path in usd_ops.list_materials(stage):
                self.mat_combo.addItem(name, path)
            self.kind_combo.addItems(usd_ops.list_kinds(stage))
        if not self.mat_combo.count():
            self.mat_combo.addItem("(no materials in this stage)", None)

    def _select_by_name(self):
        stage = self._stage()
        if stage:
            self._show_results(usd_ops.find_by_name(stage, self.name_edit.text()),
                               "Name match")

    def _select_by_material(self):
        stage = self._stage()
        path = self.mat_combo.currentData()
        if stage and path:
            self._show_results(usd_ops.find_by_material(stage, path), "Material match")

    def _select_by_kind(self):
        stage = self._stage()
        kind = self.kind_combo.currentText()
        if stage and kind:
            self._show_results(usd_ops.find_by_kind(stage, kind), "Kind '{}'".format(kind))

    def _select_invisible(self):
        stage = self._stage()
        if stage:
            self._show_results(usd_ops.find_invisible(stage), "Invisible")

    def _unload(self):
        stage, prims = self._stage(), self._target_prims()
        if stage and prims:
            n = usd_ops.unload_prims(stage, prims)
            self.status.setText("Unloaded payloads on {} prim(s)".format(n))

    def _load_selected(self):
        stage, prims = self._stage(), self._target_prims()
        if stage and prims:
            n = usd_ops.load_prims(stage, prims)
            self.status.setText("Loaded payloads on {} prim(s)".format(n))

    def _make_visible(self):
        prims = self._target_prims()
        if prims:
            n = usd_ops.make_visible(prims)
            self.status.setText("Made {} prim(s) visible".format(n))

    def _select_from_list(self):
        rows = [self.result_list.row(i) for i in self.result_list.selectedItems()]
        usd_ops.select_prims(self._proxy(), [self._results[r] for r in rows])


def show():
    """Create (or recreate) and show the tool window."""
    global _window
    if _window is not None:
        _window.close()
        _window.deleteLater()
    _window = UsdUtilityWindow()
    _window.show()
    return _window
