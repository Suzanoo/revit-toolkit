# # -*- coding: utf-8 -*-

# from Autodesk.Revit.DB import *
# from Autodesk.Revit.UI.Selection import ObjectType
# from pyrevit import revit, forms

# uidoc = revit.uidoc
# doc = revit.doc
# view = doc.ActiveView


# def get_length_m(wall):
#     p = wall.get_Parameter(BuiltInParameter.CURVE_ELEM_LENGTH)
#     if not p:
#         return 0.0
#     return UnitUtils.ConvertFromInternalUnits(p.AsDouble(), UnitTypeId.Meters)


# def get_area_m2(wall):
#     p = wall.get_Parameter(BuiltInParameter.HOST_AREA_COMPUTED)
#     if not p:
#         return 0.0
#     return UnitUtils.ConvertFromInternalUnits(p.AsDouble(), UnitTypeId.SquareMeters)


# try:
#     ref = uidoc.Selection.PickObject(
#         ObjectType.PointOnElement,
#         "Click Wall"
#     )

#     wall = doc.GetElement(ref.ElementId)

#     if not isinstance(wall, Wall):
#         forms.alert("ตัวที่คลิกไม่ใช่ Wall")
#         raise SystemExit

#     length_m = get_length_m(wall)
#     area_m2 = get_area_m2(wall)

#     text_value = (
#         "Length = {:.2f} m\n"
#         "Area = {:.2f} m²"
#     ).format(length_m, area_m2)

#     pt = uidoc.Selection.PickPoint("Pick point to place text")

#     text_type_id = doc.GetDefaultElementTypeId(
#         ElementTypeGroup.TextNoteType
#     )

#     with revit.Transaction("Place Wall Text"):
#         TextNote.Create(
#             doc,
#             view.Id,
#             pt,
#             text_value,
#             text_type_id
#         )

# except Exception as e:
#     forms.alert("Wall Tag Error:\n\n{}".format(str(e)))

# -*- coding: utf-8 -*-

# -*- coding: utf-8 -*-

from Autodesk.Revit.DB import *
from Autodesk.Revit.UI.Selection import ObjectType, ISelectionFilter
from pyrevit import revit, forms

uidoc = revit.uidoc
doc = revit.doc
view = doc.ActiveView


class WallFilter(ISelectionFilter):

    def AllowElement(self, elem):
        return isinstance(elem, Wall)

    def AllowReference(self, reference, point):
        return True


def get_length_m(wall):

    p = wall.get_Parameter(
        BuiltInParameter.CURVE_ELEM_LENGTH
    )

    if not p:
        return 0.0

    return UnitUtils.ConvertFromInternalUnits(
        p.AsDouble(),
        UnitTypeId.Meters
    )


def get_area_m2(wall):

    p = wall.get_Parameter(
        BuiltInParameter.HOST_AREA_COMPUTED
    )

    if not p:
        return 0.0

    return UnitUtils.ConvertFromInternalUnits(
        p.AsDouble(),
        UnitTypeId.SquareMeters
    )


try:

    refs = uidoc.Selection.PickObjects(
        ObjectType.Element,
        WallFilter(),
        "Pick Walls then Finish"
    )

    walls = []
    seen = set()

    for r in refs:

        wall = doc.GetElement(r.ElementId)

        if isinstance(wall, Wall):

            wid = wall.Id.Value

            if wid not in seen:
                seen.add(wid)
                walls.append(wall)

    if not walls:
        forms.alert("No Walls Selected")
        raise SystemExit

    total_length = sum(
        get_length_m(w) for w in walls
    )

    total_area = sum(
        get_area_m2(w) for w in walls
    )

    text_value = (
        "L = {:.2f} m\n"
        "A = {:.2f} m²"
    ).format(
        total_length,
        total_area
    )

    pt = uidoc.Selection.PickPoint(
        "Pick text location"
    )

    text_type_id = doc.GetDefaultElementTypeId(
        ElementTypeGroup.TextNoteType
    )

    with revit.Transaction("Place Wall Text"):

        TextNote.Create(
            doc,
            view.Id,
            pt,
            text_value,
            text_type_id
        )

except Exception as e:

    forms.alert(
        "Wall Tag Error:\n\n{}".format(str(e))
    )