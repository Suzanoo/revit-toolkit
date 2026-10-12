# -*- coding: utf-8 -*-
from pyrevit import revit, script
from Autodesk.Revit.DB import ImportInstance, FilteredElementCollector, ElementId

doc = revit.doc
output = script.get_output()

cad_instances = list(FilteredElementCollector(doc).OfClass(ImportInstance))

print("พบ CAD ทั้งหมด: {} รายการ".format(len(cad_instances)))
print("-" * 60)

if not cad_instances:
    print("ไม่พบ CAD Import / Link ใน project นี้")
else:
    for i, cad in enumerate(cad_instances, 1):
        # ชื่อ
        try:
            name = cad.Name
        except:
            name = "Unknown"

        # Link / Import
        try:
            is_linked = cad.IsLinked
            cad_type = "Link" if is_linked else "Import"
        except:
            cad_type = "Unknown"

        # Pinned
        try:
            pinned = cad.Pinned
        except:
            pinned = "Unknown"

        # Owner view
        view_name = "Model / Not view-specific"
        try:
            owner_view_id = cad.OwnerViewId
            if owner_view_id and owner_view_id != ElementId.InvalidElementId:
                view = doc.GetElement(owner_view_id)
                if view:
                    view_name = view.Name
        except:
            view_name = "Unknown View"

        print("No. {}".format(i))
        print("Name      : {}".format(name))
        print("Type      : {}".format(cad_type))
        print("Pinned    : {}".format(pinned))
        print("View      : {}".format(view_name))
        print("-" * 60)