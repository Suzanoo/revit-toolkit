# -*- coding: utf-8 -*-

from pyrevit import revit, script
from Autodesk.Revit.DB import *

doc = revit.doc
out = script.get_output()

walls = (
    FilteredElementCollector(doc)
    .OfCategory(BuiltInCategory.OST_Walls)
    .WhereElementIsNotElementType()
    .ToElements()
)

data = {}

def safe_name(elem):
    try:
        return Element.Name.GetValue(elem)
    except:
        try:
            return elem.Name
        except:
            return "Unknown"

for w in walls:

    try:
        # WALL TYPE
        wall_type = doc.GetElement(w.GetTypeId())
        type_name = safe_name(wall_type)

        # LEVEL
        level_param = w.get_Parameter(
            BuiltInParameter.WALL_BASE_CONSTRAINT
        )

        if level_param:
            level = doc.GetElement(level_param.AsElementId())
            level_name = safe_name(level)
        else:
            level_name = "No Level"

        # LENGTH
        length_param = w.get_Parameter(
            BuiltInParameter.CURVE_ELEM_LENGTH
        )

        if length_param:
            length_ft = length_param.AsDouble()
        else:
            length_ft = 0

        # AREA
        area_param = w.get_Parameter(
            BuiltInParameter.HOST_AREA_COMPUTED
        )

        if area_param:
            area_ft2 = area_param.AsDouble()
        else:
            area_ft2 = 0

        # INIT
        if level_name not in data:
            data[level_name] = {}

        if type_name not in data[level_name]:
            data[level_name][type_name] = {
                "length": 0,
                "area": 0
            }

        # SUM
        data[level_name][type_name]["length"] += length_ft
        data[level_name][type_name]["area"] += area_ft2

    except Exception as e:
        out.print_md("ERROR: {}".format(str(e)))

# REPORT
out.print_md("# Wall Summary")
out.print_md("---")

for level_name in sorted(data.keys()):

    out.print_md("## {}".format(level_name))

    for type_name in sorted(data[level_name].keys()):

        length_m = (
            data[level_name][type_name]["length"] * 0.3048
        )

        area_m2 = (
            data[level_name][type_name]["area"] * 0.09290304
        )

        out.print_md(
            "- **{}**".format(type_name)
        )

        out.print_md(
            "  - Length = {:.2f} m".format(length_m)
        )

        out.print_md(
            "  - Area = {:.2f} m²".format(area_m2)
        )

    out.print_md("---")