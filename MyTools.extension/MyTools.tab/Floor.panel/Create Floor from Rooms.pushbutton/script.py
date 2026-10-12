# -*- coding: utf-8 -*-
"""
Create Floor from Rooms
Revit 2026 / pyRevit 6.x

Workflow
1. Preselect one or more Rooms, or start the command and select Rooms.
2. Select an existing Floor Type.
3. Use the selected type or duplicate it with a new name.
4. Create one Floor per Room using the Room Level and Room boundaries.
"""

from System.Collections.Generic import List

from Autodesk.Revit.DB import (
    BuiltInCategory,
    BuiltInParameter,
    CurveLoop,
    ElementId,
    FilteredElementCollector,
    Floor,
    FloorType,
    SpatialElementBoundaryOptions,
    Transaction,
)
from Autodesk.Revit.UI.Selection import ISelectionFilter, ObjectType

from pyrevit import DB, forms, revit, script


doc = revit.doc
uidoc = revit.uidoc
output = script.get_output()

COMMAND_TITLE = "Create Floor from Rooms"


# ----------------------------------------------------------------------
# Revit version compatibility
# ----------------------------------------------------------------------

def element_id_value(element_id):
    """
    Return an integer value from ElementId.

    Revit 2024+ uses ElementId.Value (Int64).
    Older Revit versions use ElementId.IntegerValue (Int32).
    """
    if element_id is None:
        return None

    try:
        return int(element_id.Value)
    except AttributeError:
        return int(element_id.IntegerValue)


ROOM_CATEGORY_ID = element_id_value(ElementId(BuiltInCategory.OST_Rooms))
INVALID_ELEMENT_ID = element_id_value(ElementId.InvalidElementId)


def element_type_name(element_type):
    """Return a reliable type name in IronPython / Revit 2026.

    Direct access through ``element_type.Name`` can raise
    MissingMemberException in some pyRevit IronPython environments.
    """
    if element_type is None:
        return "<Unnamed Type>"

    try:
        parameter = element_type.get_Parameter(BuiltInParameter.SYMBOL_NAME_PARAM)
        if parameter:
            value = parameter.AsString()
            if value:
                return value
    except Exception:
        pass

    try:
        return DB.Element.Name.GetValue(element_type)
    except Exception:
        return "Type {}".format(element_id_value(element_type.Id))


# ----------------------------------------------------------------------
# Selection
# ----------------------------------------------------------------------

def is_room(element):
    """Return True only when the element belongs to OST_Rooms."""
    if element is None or element.Category is None:
        return False

    try:
        return element_id_value(element.Category.Id) == ROOM_CATEGORY_ID
    except Exception:
        return False


class RoomSelectionFilter(ISelectionFilter):
    def AllowElement(self, element):
        return is_room(element)

    def AllowReference(self, reference, position):
        return False


def get_selected_rooms():
    """
    Use preselected Rooms first.
    If none are preselected, ask the user to select Rooms.
    """
    rooms = []

    for element_id in uidoc.Selection.GetElementIds():
        element = doc.GetElement(element_id)
        if is_room(element):
            rooms.append(element)

    if rooms:
        return rooms

    try:
        references = uidoc.Selection.PickObjects(
            ObjectType.Element,
            RoomSelectionFilter(),
            "Select Rooms, then click Finish",
        )
    except Exception:
        # Includes Esc / cancelled selection.
        return []

    for reference in references:
        element = doc.GetElement(reference.ElementId)
        if is_room(element):
            rooms.append(element)

    return rooms


# ----------------------------------------------------------------------
# Floor type
# ----------------------------------------------------------------------

def get_floor_types():
    floor_types = list(
        FilteredElementCollector(doc)
        .OfClass(FloorType)
        .WhereElementIsElementType()
    )

    return sorted(floor_types, key=lambda item: element_type_name(item).lower())


def duplicate_floor_type(source_type, new_name):
    """Duplicate a Floor Type and return the newly created type."""
    transaction = Transaction(doc, "Duplicate Floor Type")

    try:
        transaction.Start()
        new_type_id = source_type.Duplicate(new_name)
        transaction.Commit()
        return doc.GetElement(new_type_id)

    except Exception:
        if transaction.HasStarted():
            transaction.RollBack()
        raise


def choose_floor_type():
    floor_types = get_floor_types()

    if not floor_types:
        forms.alert(
            "ไม่พบ Floor Type ในโมเดล",
            title=COMMAND_TITLE,
            exitscript=True,
        )

    type_by_label = {}
    labels = []

    for floor_type in floor_types:
        base_label = element_type_name(floor_type)
        label = base_label

        # Keep the list deterministic even if duplicate display names exist.
        if label in type_by_label:
            label = "{} [ID {}]".format(
                base_label,
                element_id_value(floor_type.Id),
            )

        labels.append(label)
        type_by_label[label] = floor_type

    selected_label = forms.SelectFromList.show(
        labels,
        multiselect=False,
        title="Select Floor Type",
        button_name="Next",
        width=520,
        height=600,
    )

    if selected_label is None:
        return None

    selected_type = type_by_label[selected_label]

    action = forms.CommandSwitchWindow.show(
        ["Use Selected Type", "Duplicate Floor Type"],
        message="Floor Type: {}".format(element_type_name(selected_type)),
        title=COMMAND_TITLE,
    )

    if action is None:
        return None

    if action == "Use Selected Type":
        return selected_type

    new_name = forms.ask_for_string(
        default="{} - Copy".format(element_type_name(selected_type)),
        prompt="New Floor Type Name",
        title="Duplicate Floor Type",
    )

    if not new_name:
        return None

    new_name = new_name.strip()

    if not new_name:
        return None

    existing_names = set(element_type_name(item).lower() for item in floor_types)

    if new_name.lower() in existing_names:
        forms.alert(
            'Floor Type ชื่อ "{}" มีอยู่แล้ว'.format(new_name),
            title="Duplicate Floor Type",
        )
        return None

    try:
        return duplicate_floor_type(selected_type, new_name)
    except Exception as error:
        forms.alert(
            "Duplicate Floor Type ไม่สำเร็จ\n\n{}".format(error),
            title="Duplicate Floor Type",
        )
        return None


# ----------------------------------------------------------------------
# Room data and boundaries
# ----------------------------------------------------------------------

def room_label(room):
    try:
        number = room.Number or "-"
    except Exception:
        number = "-"

    try:
        parameter = room.get_Parameter(BuiltInParameter.ROOM_NAME)
        name = parameter.AsString() if parameter else None
        name = name or "-"
    except Exception:
        name = "-"

    return "{} - {}".format(number, name)


def room_has_valid_level(room):
    try:
        return element_id_value(room.LevelId) != INVALID_ELEMENT_ID
    except Exception:
        return False


def build_room_profile(room):
    """
    Convert Room boundaries to IList[CurveLoop] for Floor.Create.

    The first loop is normally the exterior boundary.
    Additional loops are treated as internal openings.
    """
    options = SpatialElementBoundaryOptions()
    boundary_sets = room.GetBoundarySegments(options)

    if boundary_sets is None or boundary_sets.Count == 0:
        return None

    profile = List[CurveLoop]()

    for boundary_segments in boundary_sets:
        if boundary_segments is None or boundary_segments.Count == 0:
            continue

        curve_loop = CurveLoop()
        curve_count = 0

        for segment in boundary_segments:
            curve = segment.GetCurve()

            if curve is None:
                continue

            curve_loop.Append(curve)
            curve_count += 1

        if curve_count > 0:
            profile.Add(curve_loop)

    if profile.Count == 0:
        return None

    return profile


# ----------------------------------------------------------------------
# Floor creation
# ----------------------------------------------------------------------

def set_source_comment(floor, label):
    """Write the source Room into the Floor instance Comments."""
    parameter = floor.get_Parameter(BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS)

    if parameter is not None and not parameter.IsReadOnly:
        parameter.Set("Created from Room {}".format(label))


def create_floor_for_room(room, floor_type):
    """
    Create one Floor in its own Transaction.

    A failed Room is rolled back independently and does not cancel floors
    successfully created from other Rooms.
    """
    label = room_label(room)

    try:
        if room.Area <= 0:
            return None, "Room ไม่มีพื้นที่หรือยังไม่ Enclosed"

        if not room_has_valid_level(room):
            return None, "Room ไม่มี Level"

        profile = build_room_profile(room)

        if profile is None:
            return None, "อ่าน Room Boundary ไม่ได้"

    except Exception as error:
        return None, "ตรวจสอบ Room ไม่สำเร็จ: {}".format(error)

    transaction = Transaction(doc, "Create Floor - {}".format(label))

    try:
        transaction.Start()

        floor = Floor.Create(
            doc,
            profile,
            floor_type.Id,
            room.LevelId,
        )

        if floor is None:
            raise Exception("Revit ไม่ได้คืนค่า Floor ที่สร้าง")

        set_source_comment(floor, label)

        floor_id = element_id_value(floor.Id)
        transaction.Commit()

        return floor_id, None

    except Exception as error:
        if transaction.HasStarted():
            transaction.RollBack()

        return None, str(error)


def create_floors(rooms, floor_type):
    created = []
    skipped = []

    for room in rooms:
        label = room_label(room)
        floor_id, error = create_floor_for_room(room, floor_type)

        if error is None:
            created.append((label, floor_id))
        else:
            skipped.append((label, error))

    return created, skipped


# ----------------------------------------------------------------------
# Output
# ----------------------------------------------------------------------

def show_result(created, skipped, floor_type):
    output.print_md("# Create Floors from Rooms")
    output.print_md("**Floor Type:** {}".format(element_type_name(floor_type)))
    output.print_md(
        "**Created:** {} &nbsp;&nbsp; **Skipped:** {}".format(
            len(created),
            len(skipped),
        )
    )

    if created:
        output.print_md("## Created")
        for label, floor_id in created:
            output.print_md(
                "- {} | Floor ID `{}`".format(label, floor_id)
            )

    if skipped:
        output.print_md("## Skipped")
        for label, reason in skipped:
            output.print_md(
                "- **{}** — {}".format(label, reason)
            )

    forms.alert(
        "สร้าง Floor สำเร็จ {} ห้อง\nข้าม {} ห้อง\n\n"
        "ดูรายละเอียดใน pyRevit Output".format(
            len(created),
            len(skipped),
        ),
        title=COMMAND_TITLE,
    )


# ----------------------------------------------------------------------
# Entry point
# ----------------------------------------------------------------------

def main():
    rooms = get_selected_rooms()

    if not rooms:
        forms.alert(
            "ยังไม่ได้เลือก Room",
            title=COMMAND_TITLE,
            exitscript=True,
        )

    floor_type = choose_floor_type()

    if floor_type is None:
        return

    confirmed = forms.alert(
        "Selected Rooms : {}\n"
        "Floor Type    : {}\n\n"
        "สร้าง Floor ตอนนี้หรือไม่?".format(
            len(rooms),
            element_type_name(floor_type),
        ),
        title=COMMAND_TITLE,
        yes=True,
        no=True,
    )

    if not confirmed:
        return

    created, skipped = create_floors(rooms, floor_type)
    show_result(created, skipped, floor_type)


if __name__ == "__main__":
    main()
