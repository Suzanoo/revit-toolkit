# -*- coding: utf-8 -*-
from pyrevit import revit, DB, forms
from grid_engine import get_revit_display_position_mm, classify_rows, get_position_mm

doc = revit.doc

def mm_to_internal(mm_value):
    try:
        return DB.UnitUtils.ConvertToInternalUnits(float(mm_value), DB.UnitTypeId.Millimeters)
    except:
        return DB.UnitUtils.ConvertToInternalUnits(float(mm_value), DB.DisplayUnitType.DUT_MILLIMETERS)

def _safe_float(text, default=0.0):
    try:
        return float(text)
    except:
        return float(default)

def _get_h_total_mm(rows, mode):
    h_rows = [r for r in rows if r['direction'] == 'H']
    if not h_rows:
        return 0.0
    positions = [get_position_mm(r, mode) for r in h_rows]
    return max(positions)

def _grid_curve_from_row(row, mode, meta, h_total_mm):
    origin_x_mm = _safe_float(meta.get('origin_x', 0.0), 0.0)
    origin_y_mm = _safe_float(meta.get('origin_y', 0.0), 0.0)

    pos_mm = get_revit_display_position_mm(row, mode, h_total_mm=h_total_mm)
    length_mm = row.get('length_mm', 20000.0)

    ox = mm_to_internal(origin_x_mm)
    oy = mm_to_internal(origin_y_mm)
    pos = mm_to_internal(pos_mm)
    length = mm_to_internal(length_mm)

    direction = row['direction'].upper()

    if direction == 'V':
        p0 = DB.XYZ(ox + pos, oy, 0.0)
        p1 = DB.XYZ(ox + pos, oy + length, 0.0)
    elif direction == 'H':
        p0 = DB.XYZ(ox, oy + pos, 0.0)
        p1 = DB.XYZ(ox + length, oy + pos, 0.0)
    else:
        raise Exception('Unsupported direction: {}'.format(direction))

    return DB.Line.CreateBound(p0, p1)

def _find_existing_grids():
    found = {}
    collector = DB.FilteredElementCollector(doc).OfClass(DB.Grid)
    for g in collector:
        try:
            found[g.Name] = g
        except:
            pass
    return found

def _set_grid_bubbles(grid, active_view):
    try:
        curve = grid.Curve
        p0 = curve.GetEndPoint(0)
        p1 = curve.GetEndPoint(1)
        dx = abs(p1.X - p0.X)
        dy = abs(p1.Y - p0.Y)

        if dy >= dx:
            if p1.Y >= p0.Y:
                top_end = DB.DatumEnds.End1
                bot_end = DB.DatumEnds.End0
            else:
                top_end = DB.DatumEnds.End0
                bot_end = DB.DatumEnds.End1
            grid.ShowBubbleInView(top_end, active_view)
            grid.HideBubbleInView(bot_end, active_view)
        else:
            if p0.X <= p1.X:
                left_end = DB.DatumEnds.End0
                right_end = DB.DatumEnds.End1
            else:
                left_end = DB.DatumEnds.End1
                right_end = DB.DatumEnds.End0
            grid.ShowBubbleInView(left_end, active_view)
            grid.HideBubbleInView(right_end, active_view)
    except:
        pass

def apply_grid_mode_to_model(rows, meta, mode):
    existing = _find_existing_grids()
    active_view = doc.ActiveView
    created, updated, skipped = [], [], []
    h_total_mm = _get_h_total_mm(rows, mode)

    with revit.Transaction('Grid Decision Manager V2 - {}'.format(mode)):
        for row in rows:
            name = row['name']
            try:
                curve = _grid_curve_from_row(row, mode, meta, h_total_mm)
                if name in existing:
                    grid = existing[name]
                    grid.Curve = curve
                    updated.append(name)
                else:
                    grid = DB.Grid.Create(doc, curve)
                    grid.Name = name
                    created.append(name)
                _set_grid_bubbles(grid, active_view)
            except Exception as ex:
                skipped.append('{} ({})'.format(name, ex))

    v_rows, h_rows = classify_rows(rows)
    return {
        'created': created,
        'updated': updated,
        'skipped': skipped,
        'v_count': len(v_rows),
        'h_count': len(h_rows),
        'h_total_mm': h_total_mm,
    }

def show_summary_dialog(mode, result, grid_csv, meta_csv):
    lines = [
        'Mode: {}'.format(mode),
        'Grid CSV: {}'.format(grid_csv),
        'Meta CSV: {}'.format(meta_csv),
        '',
        'Created: {}'.format(len(result['created'])),
        'Updated: {}'.format(len(result['updated'])),
        'Skipped: {}'.format(len(result['skipped'])),
        'V grids: {}'.format(result['v_count']),
        'H grids: {}'.format(result['h_count']),
        'H display total mm (top -> bottom): {:.0f}'.format(result['h_total_mm']),
        '',
        'H grid rule: CSV is read top -> bottom, then reversed for Revit display.',
    ]
    if result['skipped']:
        lines.extend(['', 'Skipped items:'])
        for item in result['skipped'][:15]:
            lines.append('- {}'.format(item))
    forms.alert('\n'.join(lines), title='Grid Decision Manager V2')
