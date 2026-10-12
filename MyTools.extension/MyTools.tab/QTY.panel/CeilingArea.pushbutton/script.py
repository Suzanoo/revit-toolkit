# -*- coding: utf-8 -*-

from pyrevit import revit, script
from Autodesk.Revit.DB import *

doc = revit.doc
out = script.get_output()

ceilings = (
    FilteredElementCollector(doc)
    .OfCategory(BuiltInCategory.OST_Ceilings)
    .WhereElementIsNotElementType()
    .ToElements()
)

data = {}
grand_total_ft2 = 0

def safe_name(elem):
    try:
        return Element.Name.GetValue(elem)
    except:
        try:
            return elem.Name
        except:
            return "Unknown"

for c in ceilings:
    try:
        ceiling_type = doc.GetElement(c.GetTypeId())
        type_name = safe_name(ceiling_type)

        area_param = c.get_Parameter(BuiltInParameter.HOST_AREA_COMPUTED)
        if not area_param:
            continue

        area_ft2 = area_param.AsDouble()
        if area_ft2 <= 0:
            continue

        level_param = c.get_Parameter(BuiltInParameter.LEVEL_PARAM)
        if not level_param:
            level_name = "No Level"
        else:
            level = doc.GetElement(level_param.AsElementId())
            level_name = safe_name(level)

        if level_name not in data:
            data[level_name] = {}

        data[level_name][type_name] = data[level_name].get(type_name, 0) + area_ft2
        grand_total_ft2 += area_ft2

    except Exception as e:
        out.print_md("ERROR: {}".format(str(e)))

out.print_md("# Ceiling Area Summary - Whole Model")
out.print_md("---")

for level_name in sorted(data.keys()):
    level_total_ft2 = sum(data[level_name].values())

    out.print_md("## {}".format(level_name))

    for type_name, area_ft2 in sorted(data[level_name].items()):
        area_m2 = area_ft2 * 0.09290304
        out.print_md("- **{}** = {:.2f} m²".format(type_name, area_m2))

    out.print_md("**Level Total = {:.2f} m²**".format(level_total_ft2 * 0.09290304))
    out.print_md("---")

out.print_md("# GRAND TOTAL = {:.2f} m²".format(grand_total_ft2 * 0.09290304))