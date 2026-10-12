# -*- coding: utf-8 -*-

def _fmt(v):
    try:
        return '{:.0f}'.format(float(v))
    except:
        return str(v)

def build_compare_text(rows, max_items=50):
    lines = []
    lines.append('Grid Compare Summary')
    lines.append('')

    show_rows = rows[:max_items]
    for row in show_rows:
        lines.append(
            '{name} [{direction}]  D={d}  F={f}  A={a}  active={m}'.format(
                name=row['name'],
                direction=row['direction'],
                d=_fmt(row['position_design_mm']),
                f=_fmt(row['position_field_mm']),
                a=_fmt(row['position_adjust_mm']),
                m=row.get('active_mode', 'DESIGN'),
            )
        )

    if len(rows) > max_items:
        lines.append('')
        lines.append('... truncated {} more rows'.format(len(rows) - max_items))

    lines.append('')
    lines.append('Note: H grid is displayed in Revit as top -> bottom by reversing Y positions.')
    return '\n'.join(lines)
