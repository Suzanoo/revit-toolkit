# -*- coding: utf-8 -*-

from Autodesk.Revit.DB import *
from Autodesk.Revit.UI.Selection import ObjectSnapTypes
from pyrevit import revit, forms
import traceback

uidoc = revit.uidoc
doc = revit.doc
view = doc.ActiveView


def ensure_workplane():
    z = 0
    if view.GenLevel:
        z = view.GenLevel.Elevation

    plane = Plane.CreateByNormalAndOrigin(XYZ.BasisZ, XYZ(0, 0, z))

    with revit.Transaction("Set Work Plane"):
        sp = SketchPlane.Create(doc, plane)
        view.SketchPlane = sp


def get_area_m2(elem):
    p = elem.get_Parameter(BuiltInParameter.HOST_AREA_COMPUTED)
    if not p:
        return None

    return UnitUtils.ConvertFromInternalUnits(
        p.AsDouble(),
        UnitTypeId.SquareMeters
    )


def point_in_poly_xy(pt, poly):
    x = pt.X
    y = pt.Y
    inside = False
    j = len(poly) - 1

    for i in range(len(poly)):
        xi = poly[i].X
        yi = poly[i].Y
        xj = poly[j].X
        yj = poly[j].Y

        if ((yi > y) != (yj > y)):
            x_int = (xj - xi) * (y - yi) / ((yj - yi) + 0.0000001) + xi
            if x < x_int:
                inside = not inside

        j = i

    return inside


def polygon_area_xy(points):
    area = 0.0

    for i in range(len(points)):
        j = (i + 1) % len(points)
        area += points[i].X * points[j].Y
        area -= points[j].X * points[i].Y

    return abs(area) / 2.0


def loop_to_points(loop, transform):
    pts = []

    for curve in loop:
        for p in curve.Tessellate():
            p2 = transform.OfPoint(p)

            if not pts or p2.DistanceTo(pts[-1]) > 0.0001:
                pts.append(p2)

    return pts


def collect_solids(geo, transform):
    solids = []

    if not geo:
        return solids

    for g in geo:

        if isinstance(g, Solid):
            if g.Faces.Size > 0 and g.Volume > 0:
                solids.append((g, transform))

        elif isinstance(g, GeometryInstance):
            inst_transform = transform.Multiply(g.Transform)
            inst_geo = g.GetInstanceGeometry()
            solids.extend(collect_solids(inst_geo, inst_transform))

    return solids


def ceiling_contains_point(ceiling, pt):
    opt = Options()
    opt.ComputeReferences = False
    opt.DetailLevel = ViewDetailLevel.Fine
    opt.IncludeNonVisibleObjects = True

    geo = ceiling.get_Geometry(opt)

    solids = collect_solids(geo, Transform.Identity)

    for solid, transform in solids:

        for face in solid.Faces:

            pf = face if isinstance(face, PlanarFace) else None
            if not pf:
                continue

            normal = transform.OfVector(pf.FaceNormal)

            # เอาเฉพาะหน้าราบแนวนอน ทั้งบน/ล่าง
            if abs(normal.Z) < 0.85:
                continue

            loops = []

            for cl in pf.GetEdgesAsCurveLoops():
                pts = loop_to_points(cl, transform)

                if len(pts) >= 3:
                    loops.append(pts)

            if not loops:
                continue

            loops.sort(key=polygon_area_xy, reverse=True)

            outer = loops[0]
            holes = loops[1:]

            if not point_in_poly_xy(pt, outer):
                continue

            in_hole = False
            for h in holes:
                if point_in_poly_xy(pt, h):
                    in_hole = True
                    break

            if not in_hole:
                return True

    return False


try:
    ensure_workplane()

    pt = uidoc.Selection.PickPoint(
        ObjectSnapTypes.None,
        "Click inside CEILING area"
    )

    ceilings = FilteredElementCollector(doc, view.Id)\
    .OfCategory(BuiltInCategory.OST_Ceilings)\
    .WhereElementIsNotElementType()\
    .ToElements()

    matched = []

    for c in ceilings:
        try:
            if ceiling_contains_point(c, pt):
                area = get_area_m2(c)
                if area:
                    matched.append((c, area))
        except:
            pass

    if not matched:
        forms.alert(
            "ไม่เจอฝ้าใต้จุดที่คลิก\n\n"
            "เช็ก 2 อย่าง:\n"
            "1) จุดที่คลิกอยู่บน Hatch ฝ้าจริงไหม\n"
            "2) ฝ้านั้นเป็น Ceiling จริง ไม่ใช่ Filled Region / Detail Item"
        )
        raise SystemExit

    # สำหรับฝ้า ให้เลือกพื้นที่ใหญ่สุด ไม่ใช่เล็กสุด
    matched.sort(key=lambda x: x[1], reverse=True)
    ceiling, area_m2 = matched[0]

    text_value = "{:.2f} m²".format(area_m2)

    text_type_id = doc.GetDefaultElementTypeId(
        ElementTypeGroup.TextNoteType
    )

    with revit.Transaction("Place Ceiling Area Text"):
        TextNote.Create(
            doc,
            view.Id,
            pt,
            text_value,
            text_type_id
        )

except Exception as e:
    forms.alert(
        "Ceiling Area Tag Error:\n\n{}\n\n{}".format(
            str(e),
            traceback.format_exc()
        )
    )