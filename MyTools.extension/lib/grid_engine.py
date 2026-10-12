# -*- coding: utf-8 -*-

def get_position_mm(row, mode):
    mode = (mode or '').upper()
    if mode == 'DESIGN':
        return row['position_design_mm']
    elif mode == 'FIELD':
        return row['position_field_mm']
    elif mode == 'ADJUST':
        return row['position_adjust_mm']
    elif mode == 'ACTIVE':
        active_mode = row.get('active_mode', 'DESIGN').upper()
        return get_position_mm(row, active_mode)
    else:
        raise Exception('Unsupported mode: {}'.format(mode))

def classify_rows(rows):
    v_rows = []
    h_rows = []
    for row in rows:
        if row['direction'] == 'V':
            v_rows.append(row)
        elif row['direction'] == 'H':
            h_rows.append(row)
    return v_rows, h_rows

def get_revit_display_position_mm(row, mode, h_total_mm=None):
    pos_mm = get_position_mm(row, mode)
    if row['direction'] == 'H':
        total = float(h_total_mm or 0.0)
        return total - pos_mm
    return pos_mm
