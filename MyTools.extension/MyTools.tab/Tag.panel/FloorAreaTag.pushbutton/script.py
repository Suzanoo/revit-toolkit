# -*- coding: utf-8 -*-

from Autodesk.Revit.DB import *
from Autodesk.Revit.UI.Selection import ObjectSnapTypes
from pyrevit import revit, forms

uidoc = revit.uidoc
doc = revit.doc
view = doc.ActiveView


def get_floor_area_m2(floor):
    p = floor.get_Parameter(BuiltInParameter.HOST_AREA_COMPUTED)
    if not p:
        return None
    return UnitUtils.ConvertFromInternalUnits(p.AsDouble(), UnitTypeId.SquareMeters)


def point_in_poly_xy(pt, poly):
    x = pt.X
    y = pt.Y
    inside = False
    n = len(poly)

    j = n - 1
    for i in range(n):
        xi, yi = poly[i].X, poly[i].Y
        xj, yj = poly[j].X, poly[j].Y

        if ((yi > y) != (yj > y)):
            x_intersect = (xj - xi) * (y - yi) / (yj - yi + 0.0000001) + xi
            if x < x_intersect:
                inside = not inside
        j = i

    return inside


def loop_to_points(loop):
    pts = []
    for curve in loop:
        for p in curve.Tessellate():
            if not pts or p.DistanceTo(pts[-1]) > 0.0001:
                pts.append(p)
    return pts


def polygon_area_xy(points):
    area = 0.0
    n = len(points)
    for i in range(n):
        j = (i + 1) % n
        area += points[i].X * points[j].Y
        area -= points[j].X * points[i].Y
    return abs(area) / 2.0


def floor_contains_point(floor, pt):
    opt = Options()
    opt.ComputeReferences = True
    opt.DetailLevel = ViewDetailLevel.Fine

    geo = floor.get_Geometry(opt)
    if not geo:
        return False

    loops_found = []

    for g in geo:
        solid = g if isinstance(g, Solid) else None
        if not solid or solid.Faces.Size == 0:
            continue

        for face in solid.Faces:
            pf = face if isinstance(face, PlanarFace) else None
            if not pf:
                continue

            # เอาเฉพาะหน้าบนของพื้น
            if pf.FaceNormal.Z < 0.9:
                continue

            curve_loops = pf.GetEdgesAsCurveLoops()
            for cl in curve_loops:
                pts = loop_to_points(cl)
                if len(pts) >= 3:
                    loops_found.append(pts)

    if not loops_found:
        return False

    # outer loop = พื้นที่ใหญ่สุด
    loops_found.sort(key=polygon_area_xy, reverse=True)
    outer = loops_found[0]
    holes = loops_found[1:]

    if not point_in_poly_xy(pt, outer):
        return False

    for h in holes:
        if point_in_poly_xy(pt, h):
            return False

    return True


# -----------------------------
# Main
# -----------------------------

try:
    pt = uidoc.Selection.PickPoint("Click inside FLOOR area to place area text")
except:
    raise SystemExit

floors = FilteredElementCollector(doc, view.Id)\
    .OfCategory(BuiltInCategory.OST_Floors)\
    .WhereElementIsNotElementType()\
    .ToElements()

matched = []

for f in floors:
    try:
        if floor_contains_point(f, pt):
            area = get_floor_area_m2(f)
            if area:
                matched.append((f, area))
    except:
        pass

if not matched:
    forms.alert("ไม่เจอพื้นใต้จุดที่คลิก")
    raise SystemExit

# ถ้าเจอหลายพื้นซ้อนกัน เลือกพื้นที่เล็กสุดก่อน เช่น floor finish
matched.sort(key=lambda x: x[1])
floor, area_m2 = matched[0]

text_value = "{:.2f} m²".format(area_m2)

text_type_id = doc.GetDefaultElementTypeId(ElementTypeGroup.TextNoteType)

with revit.Transaction("Place Floor Area Text"):
    TextNote.Create(doc, view.Id, pt, text_value, text_type_id)