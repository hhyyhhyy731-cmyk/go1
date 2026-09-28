"""usage: python3 build_hwpx.py out.hwpx [module]  — content.py 블록을 한글(HWPX)로 출력"""
import sys
import warnings
from hwpx import HwpxDocument
import importlib
from content import BLUE
blocks = importlib.import_module(sys.argv[2] if len(sys.argv) > 2 else 'content').blocks

warnings.filterwarnings('ignore', category=DeprecationWarning)

FONT = '맑은 고딕'
MM = 283.465              # HWPUNIT per mm
W = round(180 * MM)       # A4 210mm - 15mm x 2
LABEL_W = round(40 * MM)

d = HwpxDocument.new()
d.set_page_margins(left=round(15 * MM), right=round(15 * MM), top=round(12 * MM), bottom=round(12 * MM),
                   header=0, footer=0)
header = d.oxml.headers[0]

_runs, _paras = {}, {}
def run_style(size=10, bold=False, italic=False, color=None):
    key = (size, bold, italic, color)
    if key not in _runs:
        _runs[key] = d.ensure_run_style(font=FONT, size=size, bold=bold, italic=italic,
                                        color=('#' + color) if color else None)
    return _runs[key]

def para_style(align=None, before=0, after=1.5):
    key = (align, before, after)
    if key not in _paras:
        _paras[key] = header.ensure_paragraph_format(
            alignment={'center': 'CENTER', 'right': 'RIGHT'}.get(align, 'JUSTIFY'),
            margins={'prev': round(before * 100), 'next': round(after * 100)})
    return _paras[key]

pending_break = False
def add_p(text, size=10, bold=False, italic=False, color=None, align=None, before=0, after=1.5):
    global pending_break
    p = d.add_paragraph(text, char_pr_id_ref=run_style(size, bold, italic, color),
                        para_pr_id_ref=para_style(align, before, after))
    if pending_break:
        p.element.set('pageBreak', '1')
        pending_break = False
    return p

def fill_cell(table, r, c, spec):
    cell = table.cell(r, c)
    first = True
    for line in spec['lines'] or ['']:
        f = dict(size=spec.get('size', 10), bold=spec.get('bold', False), italic=False, color=None)
        if isinstance(line, dict):
            f.update({k: line[k] for k in ('size', 'bold', 'italic', 'color') if k in line})
            line = line['t']
        cs, ps = run_style(**f), para_style(spec.get('align'), 0, 0)
        if first:
            p = cell.paragraphs[0]
            p.text = line
            p.char_pr_id_ref = cs
            p.para_pr_id_ref = ps
            for rn in p.runs:
                rn.char_pr_id_ref = cs
            first = False
        else:
            cell.add_paragraph(line, char_pr_id_ref=cs, para_pr_id_ref=ps)
    sub = cell.element.find('{*}subList')
    if sub is not None:
        sub.set('vertAlign', 'TOP' if spec.get('top') else 'CENTER')
    if spec.get('fill'):
        table.set_cell_shading(r, c, '#' + spec['fill'])

def add_table(widths, rows, heights=None):
    global pending_break
    t = d.add_table(len(rows), len(widths), width=W, char_pr_id_ref=run_style(), para_pr_id_ref=para_style())
    if pending_break:
        t.paragraph.element.set('pageBreak', '1')
        pending_break = False
    t.set_column_widths(widths)
    for r, row in enumerate(rows):
        for c, spec in enumerate(row):
            fill_cell(t, r, c, spec)
            h = (heights or [None] * len(rows))[r]
            if h:
                t.cell(r, c).set_size(height=round(h * MM))
    if heights and all(heights):
        t.element.find('{*}sz').set('height', str(sum(round(h * MM) for h in heights)))
    return t

for b in blocks:
    k = b['k']
    if k == 'title':
        add_p(b['t'], size=16, bold=True, align='center', after=3)
        if b.get('sub'):
            add_p(b['sub'], size=9, color='555555', align='center', after=5)
    elif k == 'h':
        add_p(b['t'], size=12, bold=True, before=8, after=3)
    elif k == 'p':
        add_p(b['t'], size=b.get('size', 10), bold=b.get('bold', False), italic=b.get('italic', False),
              color=b.get('color'), align=b.get('align'))
    elif k == 'brk':
        pending_break = True
    elif k == 'name':
        add_table([1, 1, 1.4], [[dict(lines=['1학년        반']), dict(lines=['번호:']), dict(lines=['이름:'])]], [10])
    elif k == 'form':
        add_table([LABEL_W, W - LABEL_W],
                  [[dict(lines=r['label'].split('\n'), fill=BLUE, bold=True, align='center'),
                    dict(lines=[dict(t=r['guide'], size=8, color='7F7F7F', italic=True)] if r['guide'] else [], top=True)]
                   for r in b['rows']],
                  [r['h'] for r in b['rows']])
    elif k == 'grid':
        add_table(b['widths'], b['rows'])
    elif k == 'lined':
        cw = round(b['crit_w'] * MM)
        rows = [[dict(lines=[dict(t=b['head'], size=8, color='7F7F7F', italic=True)], fill='F2F2F2'),
                 dict(lines=['기준'], size=8, bold=True, align='center', fill='F2F2F2')]]
        rows += [[dict(lines=[]), dict(lines=[])] for _ in range(b['n'])]
        t = add_table([W - cw, cw], rows, [7] + [b['h']] * b['n'])
        for r in range(len(rows)):
            for c in range(2):
                t.set_cell_borders(r, c, color='#A6A6A6')

print(d.validate())
d.save_to_path(sys.argv[1])
print('hwpx written')
