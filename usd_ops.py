"""USD operations for the USD Utility Tool.

Pure logic, no Qt. Everything here runs inside Maya with the maya-usd plugin
loaded. Functions work on a Usd.Stage and return Usd.Prim objects or UFE path
strings, so the UI module stays thin.
"""
import fnmatch

from maya import cmds
import maya.api.OpenMaya  # noqa: F401  (ensures Maya's Python env is ready)
import mayaUsd.ufe
import ufe
from pxr import Kind, Usd, UsdGeom, UsdShade


def _ensure_plugin():
    if not cmds.pluginInfo("mayaUsdPlugin", query=True, loaded=True):
        cmds.loadPlugin("mayaUsdPlugin")


# ---------------------------------------------------------------- loading
def load_usd_file(file_path):
    """Create a mayaUsdProxyShape for file_path. Returns the shape's long name."""
    _ensure_plugin()
    xform = cmds.createNode("transform", name="usdStage")
    shape = cmds.createNode("mayaUsdProxyShape", parent=xform, name="usdStageShape")
    cmds.setAttr(shape + ".filePath", file_path, type="string")
    cmds.connectAttr("time1.outTime", shape + ".time")
    return cmds.ls(shape, long=True)[0]


def list_proxy_shapes():
    """Long names of every USD proxy shape in the scene."""
    return cmds.ls(type="mayaUsdProxyShape", long=True) or []


def get_stage(proxy_shape):
    return mayaUsd.ufe.getStage(proxy_shape)


# ---------------------------------------------------------------- UFE helpers
def prim_to_ufe(proxy_shape, prim):
    """UFE path string for a prim, e.g. '|usdStage|usdStageShape,/Kitchen_set/Chair'."""
    return "{},{}".format(proxy_shape, prim.GetPath())


def selected_prims():
    """Usd.Prims for the USD items the artist has selected (via UFE)."""
    prims = []
    for item in ufe.GlobalSelection.get():
        path_str = ufe.PathString.string(item.path())
        prim = mayaUsd.ufe.ufePathToPrim(path_str)
        if prim and prim.IsValid():
            prims.append(prim)
    return prims


def select_prims(proxy_shape, prims):
    """Replace the Maya selection with the given prims."""
    paths = [prim_to_ufe(proxy_shape, p) for p in prims]
    selection = ufe.GlobalSelection.get()
    selection.clear()
    for path_str in paths:
        try:
            item = ufe.Hierarchy.createItem(ufe.PathString.path(path_str))
        except Exception:
            continue  # e.g. instance proxies that UFE cannot address
        if item:
            selection.append(item)
    return paths


def _traverse(stage):
    # Instance proxies are included because Kitchen Set-style scenes rely on
    # instancing for most of their props.
    return stage.Traverse(Usd.TraverseInstanceProxies(Usd.PrimDefaultPredicate))


# ---------------------------------------------------------------- find prims
def find_by_name(stage, pattern):
    """Prims whose name matches pattern (case-insensitive wildcards).

    A pattern with no wildcard is treated as 'contains'.
    """
    pattern = pattern.strip().lower()
    if not pattern:
        return []
    if not any(c in pattern for c in "*?["):
        pattern = "*{}*".format(pattern)
    return [p for p in _traverse(stage)
            if fnmatch.fnmatch(p.GetName().lower(), pattern)]


def list_materials(stage):
    """[(name, path_string)] for every UsdShade.Material on the stage."""
    return [(p.GetName(), str(p.GetPath()))
            for p in _traverse(stage) if p.IsA(UsdShade.Material)]


def find_by_material(stage, material_path):
    """Meshes/gprims whose bound material is material_path."""
    found = []
    for prim in _traverse(stage):
        if not prim.IsA(UsdGeom.Gprim):
            continue
        material, _ = UsdShade.MaterialBindingAPI(prim).ComputeBoundMaterial()
        if material and str(material.GetPath()) == material_path:
            found.append(prim)
    return found


def list_kinds(stage):
    """Sorted kinds (component, group, assembly, ...) authored on the stage."""
    kinds = set()
    for prim in _traverse(stage):
        kind = Usd.ModelAPI(prim).GetKind()
        if kind:
            kinds.add(str(kind))
    return sorted(kinds)


def find_by_kind(stage, kind):
    """Prims whose model kind is exactly `kind`."""
    return [p for p in _traverse(stage) if Usd.ModelAPI(p).GetKind() == kind]


def find_invisible(stage):
    """Top-most prims that are invisible (children of an invisible prim are skipped)."""
    found = []
    for prim in _traverse(stage):
        img = UsdGeom.Imageable(prim)
        if not img:
            continue
        if img.ComputeVisibility() != UsdGeom.Tokens.invisible:
            continue
        parent = prim.GetParent()
        parent_img = UsdGeom.Imageable(parent) if parent and parent.IsValid() else None
        if parent_img and parent_img.ComputeVisibility() == UsdGeom.Tokens.invisible:
            continue
        found.append(prim)
    return found


# ---------------------------------------------------------------- edit prims
def make_visible(prims):
    for prim in prims:
        img = UsdGeom.Imageable(prim)
        if img:
            img.MakeVisible()
    return len(prims)


def unload_prims(stage, prims):
    """Unload payloads at/under each prim. Returns how many prims were unloaded."""
    count = 0
    for prim in prims:
        stage.Unload(prim.GetPath())
        count += 1
    return count


def load_prims(stage, prims):
    """Load payloads at/under each prim."""
    for prim in prims:
        stage.Load(prim.GetPath())
    return len(prims)
