# -*- coding: utf-8 -*-

from pyrevit import revit, script
from Autodesk.Revit.DB import FilteredElementCollector, BuiltInCategory

doc = revit.doc
view = doc.ActiveView
output = script.get_output()

# เก็บ Detail Lines / Lines เฉพาะใน View ปัจจุบัน
lines = (
    FilteredElementCollector(doc, view.Id)
    .OfCategory(BuiltInCategory.OST_Lines)
    .WhereElementIsNotElementType()
    .ToElements()
)

result = {}

for line in lines:
    try:
        style_name = line.LineStyle.Name
        length_ft = line.GeometryCurve.Length
        result[style_name] = result.get(style_name, 0) + length_ft
    except:
        pass

output.print_md("# Detail Line Length Summary")
output.print_md("**View:** {}".format(view.Name))
output.print_md("---")

total_ft = 0

for style_name, length_ft in sorted(result.items()):
    length_m = length_ft * 0.3048
    total_ft += length_ft
    output.print_md("- **{}** = {:.2f} m".format(style_name, length_m))

output.print_md("---")
output.print_md("## Total = {:.2f} m".format(total_ft * 0.3048))