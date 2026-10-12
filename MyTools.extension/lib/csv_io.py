# -*- coding: utf-8 -*-
import csv

REQUIRED_GRID_COLUMNS = [
    'direction',
    'name',
    'design_spacing_mm',
    'field_spacing_mm',
    'adjust_spacing_mm',
    'position_design_mm',
    'position_field_mm',
    'position_adjust_mm',
    'length_mm',
    'active_mode',
]

def _to_float(value, default=0.0):
    try:
        if value is None or str(value).strip() == '':
            return float(default)
        return float(value)
    except Exception:
        return float(default)

def load_grid_data(csv_path):
    rows = []
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []
        missing = [c for c in REQUIRED_GRID_COLUMNS if c not in headers]
        if missing:
            raise Exception('Missing required columns in grid CSV: {}'.format(', '.join(missing)))

        for raw in reader:
            row = {
                'direction': str(raw.get('direction', '')).strip().upper(),
                'name': str(raw.get('name', '')).strip(),
                'design_spacing_mm': _to_float(raw.get('design_spacing_mm')),
                'field_spacing_mm': _to_float(raw.get('field_spacing_mm')),
                'adjust_spacing_mm': _to_float(raw.get('adjust_spacing_mm')),
                'position_design_mm': _to_float(raw.get('position_design_mm')),
                'position_field_mm': _to_float(raw.get('position_field_mm')),
                'position_adjust_mm': _to_float(raw.get('position_adjust_mm')),
                'length_mm': _to_float(raw.get('length_mm'), 20000),
                'active_mode': str(raw.get('active_mode', 'DESIGN')).strip().upper(),
                'note': str(raw.get('note', '')).strip(),
            }
            if row['name']:
                rows.append(row)
    return rows

def load_meta_data(csv_path):
    meta = {}
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for raw in reader:
            key = str(raw.get('key', '')).strip()
            val = str(raw.get('value', '')).strip()
            if key:
                meta[key] = val
    return meta

def validate_h_order_hint(rows):
    h_rows = [r for r in rows if r['direction'] == 'H']
    if not h_rows:
        return ''
    return 'H grid behavior: CSV is interpreted as top -> bottom. Script reverses H positions for Revit display.'
