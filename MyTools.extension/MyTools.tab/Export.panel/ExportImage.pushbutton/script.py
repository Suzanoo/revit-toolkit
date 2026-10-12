# -*- coding: utf-8 -*-
from pyrevit import revit, forms
from Autodesk.Revit.DB import (
    FilteredElementCollector,
    ImageExportOptions,
    ExportRange,
    ZoomFitType,
    FitDirectionType,
    ImageResolution,
    ImageFileType,
    ViewSheet
)
import os
import re
import traceback

doc = revit.doc
active_view = doc.ActiveView


def safe_name(text):
    return re.sub(r'[\\/*?:"<>|]', "_", text).strip()


def pick_export_mode():
    return forms.SelectFromList.show(
        ["Current View", "Pick Sheets"],
        title="Select Export Mode",
        multiselect=False
    )


def pick_file_type():
    return forms.SelectFromList.show(
        ["PNG", "JPG"],
        title="Select Image Type",
        multiselect=False
    )


def pick_dpi():
    choice = forms.SelectFromList.show(
        ["150 DPI", "300 DPI", "600 DPI"],
        title="Select DPI",
        multiselect=False
    )
    if not choice:
        return None

    dpi_map = {
        "150 DPI": ImageResolution.DPI_150,
        "300 DPI": ImageResolution.DPI_300,
        "600 DPI": ImageResolution.DPI_600
    }
    return choice, dpi_map[choice]


def pick_pixel_size():
    choice = forms.SelectFromList.show(
        ["5000 px", "8000 px", "10000 px"],
        title="Select Image Size",
        multiselect=False
    )
    if not choice:
        return None

    size_map = {
        "5000 px": 5000,
        "8000 px": 8000,
        "10000 px": 10000
    }
    return choice, size_map[choice]


def get_file_type(choice):
    if choice == "PNG":
        return ImageFileType.PNG
    elif choice == "JPG":
        return ImageFileType.JPEGLossless
    else:
        return ImageFileType.PNG


def build_options(file_base, image_type, dpi_value, pixel_size):
    opts = ImageExportOptions()
    opts.FilePath = file_base
    opts.ZoomType = ZoomFitType.FitToPage
    opts.FitDirection = FitDirectionType.Horizontal
    opts.PixelSize = pixel_size
    opts.ImageResolution = dpi_value
    opts.HLRandWFViewsFileType = image_type
    opts.ShadowViewsFileType = image_type
    return opts


class SheetOption(forms.TemplateListItem):
    @property
    def name(self):
        return "{} - {}".format(self.item.SheetNumber, self.item.Name)


def pick_sheets():
    all_sheets = list(
        FilteredElementCollector(doc)
        .OfClass(ViewSheet)
        .ToElements()
    )

    # ตัด placeholder sheets ออก
    real_sheets = [s for s in all_sheets if not s.IsPlaceholder]

    # เรียงตามเลข sheet
    real_sheets.sort(key=lambda s: (s.SheetNumber, s.Name))

    wrapped = [SheetOption(s) for s in real_sheets]

    selected = forms.SelectFromList.show(
        wrapped,
        title="Select Sheets to Export",
        multiselect=True,
        width=700,
        button_name="Export Selected Sheets"
    )

    if not selected:
        return []

    result = []

    for x in selected:
        if hasattr(x, "item"):
            result.append(x.item)
        else:
            result.append(x)

    return result


def export_current_view(folder, image_type, dpi_value, pixel_size):
    view_name = safe_name(active_view.Name)
    file_base = os.path.join(folder, view_name)

    opts = build_options(file_base, image_type, dpi_value, pixel_size)
    opts.ExportRange = ExportRange.CurrentView

    doc.ExportImage(opts)
    return [view_name]


def export_picked_sheets(folder, image_type, dpi_value, pixel_size):
    sheets = pick_sheets()

    if not sheets:
        forms.alert("No sheets selected.", exitscript=True)

    exported_names = []

    for sheet in sheets:
        sheet_number = safe_name(sheet.SheetNumber)
        sheet_name = safe_name(sheet.Name)
        file_name = "{} - {}".format(sheet_number, sheet_name)
        file_base = os.path.join(folder, file_name)

        opts = build_options(file_base, image_type, dpi_value, pixel_size)
        opts.ExportRange = ExportRange.SetOfViews
        opts.SetViewsAndSheets([sheet.Id])

        doc.ExportImage(opts)
        exported_names.append(file_name)

    return exported_names


try:
    mode = pick_export_mode()
    if not mode:
        forms.alert("No export mode selected.", exitscript=True)

    file_type_choice = pick_file_type()
    if not file_type_choice:
        forms.alert("No image type selected.", exitscript=True)

    dpi_result = pick_dpi()
    if not dpi_result:
        forms.alert("No DPI selected.", exitscript=True)
    dpi_choice, dpi_value = dpi_result

    size_result = pick_pixel_size()
    if not size_result:
        forms.alert("No pixel size selected.", exitscript=True)
    size_choice, pixel_size = size_result

    folder = forms.pick_folder(title="Select folder to export image")
    if not folder:
        forms.alert("No folder selected.", exitscript=True)

    image_type = get_file_type(file_type_choice)

    if mode == "Current View":
        exported = export_current_view(folder, image_type, dpi_value, pixel_size)
    else:
        exported = export_picked_sheets(folder, image_type, dpi_value, pixel_size)

    forms.alert(
        "Export completed!\n\nMode: {}\nType: {}\nDPI: {}\nSize: {}\nFiles: {}".format(
            mode,
            file_type_choice,
            dpi_choice,
            size_choice,
            len(exported)
        ),
        title="Export Done"
    )

except Exception as ex:
    forms.alert(
        "Export failed.\n\n{}\n\n{}".format(str(ex), traceback.format_exc()),
        title="Export Error"
    )