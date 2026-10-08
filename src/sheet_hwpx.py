"""흑백 인쇄용 학습지 HWPX 생성기 — 한글 기본 빈 문서(template_blank.hwpx)에 서식을 새로 정의해 쓴다.

usage: python3 sheet_hwpx.py out.hwpx module [--teacher]
  module    : 내용 모듈 이름 (예: ws_economy1) — build(sheet) 함수를 가진 .py
  --teacher : 교사용 — 빈칸에 정답을 채우고, OX·기출 정답과 해설을 문항 바로 아래에 넣는다

빈칸은 내용 안에 [[정답]] (긴 빈칸) 또는 [[정답|s]] (짧은 빈칸)로 쓴다.

글꼴: 모두 한컴산뜻돋움 (한글에 기본으로 들어 있는 글꼴)
"""
import importlib
import math
import os
import re
import sys
import zipfile
from xml.sax.saxutils import escape

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, 'template_blank.hwpx')

MM = 283.465
PAGE_W, PAGE_H = 59528, 84186
MARGIN_LR = round(15 * MM)
TEXT_W = PAGE_W - 2 * MARGIN_LR          # 본문 폭
COL_GAP = round(8 * MM)
COL_W = (TEXT_W - COL_GAP) // 2          # 2단일 때 한 단의 폭
CELL_PAD_X, CELL_PAD_Y = 400, 220

FONT_NAME = '한컴산뜻돋움'
DOTUM = BATANG = 2                       # header.xml 글꼴 번호 (빈 문서의 0·1 뒤에 한컴산뜻돋움을 2번으로 추가)
RED, BLUE = '#D00000', '#1F4E9A'         # 교사용 정답·해설 색
LINE_THIN = ('0.12 mm', '#808080')       # 표 안쪽 가는 회색 선
LINE_BLACK = ('0.12 mm', '#000000')
LINE_BOLD = ('0.4 mm', '#000000')        # 표 위아래 굵은 선
FILL_HEAD = '#DCDCDC'                    # 머리줄
FILL_LABEL = '#F0F0F0'                   # 항목 칸


class Header:
    """header.xml 에 글자 모양·문단 모양·테두리를 새로 추가한다."""

    def __init__(self, xml):
        self.xml = xml
        self._cache = {}
        self.char_base = re.search(r'<hh:charPr id="0".*?</hh:charPr>', xml, re.S).group(0)
        self.para_base = re.search(r'<hh:paraPr id="0".*?</hh:paraPr>', xml, re.S).group(0)

    def _add(self, tag, group, element_fn):
        ids = [int(i) for i in re.findall(r'<hh:%s id="(\d+)"' % tag, self.xml)]
        new_id = max(ids) + 1
        end = self.xml.index('</hh:%s>' % group)
        self.xml = self.xml[:end] + element_fn(new_id) + self.xml[end:]
        m = re.search(r'<hh:%s itemCnt="(\d+)"' % group, self.xml)
        self.xml = self.xml.replace(m.group(0), '<hh:%s itemCnt="%d"' % (group, int(m.group(1)) + 1), 1)
        return new_id

    def char(self, size, bold=False, font=BATANG, color='#000000', underline=False, shade='none', spacing=0):
        key = ('c', size, bold, font, color, underline, shade, spacing)
        if key not in self._cache:
            def make(i):
                el = self.char_base.replace('id="0"', 'id="%d"' % i, 1)
                el = re.sub(r'height="\d+"', 'height="%d"' % round(size * 100), el, count=1)
                el = re.sub(r'textColor="[^"]+"', 'textColor="%s"' % color, el, count=1)
                el = re.sub(r'shadeColor="[^"]+"', 'shadeColor="%s"' % shade, el, count=1)
                el = re.sub(r'<hh:fontRef [^>]*/>', '<hh:fontRef hangul="{0}" latin="{0}" hanja="{0}" japanese="{0}" '
                            'other="{0}" symbol="{0}" user="{0}"/>'.format(font), el)
                el = re.sub(r'<hh:spacing [^>]*/>', '<hh:spacing hangul="{0}" latin="{0}" hanja="{0}" japanese="{0}" '
                            'other="{0}" symbol="{0}" user="{0}"/>'.format(spacing), el)
                if bold:
                    el = el.replace('<hh:underline', '<hh:bold/><hh:underline', 1)
                if underline:
                    el = el.replace('<hh:underline type="NONE"', '<hh:underline type="BOTTOM"', 1)
                return el
            self._cache[key] = self._add('charPr', 'charProperties', make)
        return self._cache[key]

    def para(self, align='JUSTIFY', left=0, indent=0, prev=0, next=0, line=160, border=None, keep_next=False,
             border_offset=(0, 0, 0, 0)):
        key = ('p', align, left, indent, prev, next, line, border, keep_next, border_offset)
        if key not in self._cache:
            def make(i):
                el = self.para_base.replace('id="0"', 'id="%d"' % i, 1)
                el = re.sub(r'horizontal="\w+"', 'horizontal="%s"' % align, el, count=1)
                el = el.replace('keepWithNext="0"', 'keepWithNext="%d"' % (1 if keep_next else 0))
                margin = ('<hh:margin><hc:intent value="%d" unit="HWPUNIT"/><hc:left value="%d" unit="HWPUNIT"/>'
                          '<hc:right value="0" unit="HWPUNIT"/><hc:prev value="%d" unit="HWPUNIT"/>'
                          '<hc:next value="%d" unit="HWPUNIT"/></hh:margin>' % (indent, left, prev, next))
                el = re.sub(r'<hh:margin>.*?</hh:margin>', margin, el, flags=re.S)
                el = re.sub(r'<hh:lineSpacing type="PERCENT" value="\d+"',
                            '<hh:lineSpacing type="PERCENT" value="%d"' % line, el)
                if border is not None:
                    el = re.sub(r'<hh:border borderFillIDRef="\d+" offsetLeft="\d+" offsetRight="\d+" '
                                r'offsetTop="\d+" offsetBottom="\d+"',
                                '<hh:border borderFillIDRef="%d" offsetLeft="%d" offsetRight="%d" offsetTop="%d" '
                                'offsetBottom="%d"' % ((border,) + border_offset), el)
                return el
            self._cache[key] = self._add('paraPr', 'paraProperties', make)
        return self._cache[key]

    def border(self, top=None, bottom=None, left=None, right=None, fill=None):
        key = ('b', top, bottom, left, right, fill)
        if key not in self._cache:
            def side(name, spec):
                if spec is None:
                    return '<hh:%sBorder type="NONE" width="0.1 mm" color="#000000"/>' % name
                return '<hh:%sBorder type="SOLID" width="%s" color="%s"/>' % (name, spec[0], spec[1])

            def make(i):
                return ('<hh:borderFill id="%d" threeD="0" shadow="0" centerLine="NONE" breakCellSeparateLine="0">'
                        '<hh:slash type="NONE" Crooked="0" isCounter="0"/><hh:backSlash type="NONE" Crooked="0" '
                        'isCounter="0"/>%s%s%s%s<hh:diagonal type="SOLID" width="0.1 mm" color="#000000"/>'
                        '<hc:fillBrush><hc:winBrush faceColor="%s" hatchColor="#999999" alpha="0"/></hc:fillBrush>'
                        '</hh:borderFill>' % (i, side('left', left), side('right', right), side('top', top),
                                              side('bottom', bottom), fill or 'none'))
            self._cache[key] = self._add('borderFill', 'borderFills', make)
        return self._cache[key]


def text_width(t, size):
    """글자 폭 대략 계산 (HWPUNIT). 한글·전각은 글자 크기만큼, 영숫자·공백은 절반."""
    w = 0
    for ch in t:
        w += size * 100 * (1.0 if ord(ch) > 0x2000 else 0.5)
    return w


BLANK_LONG = '(                )'
BLANK_SHORT = '(            )'


class Sheet:
    def __init__(self, teacher=False):
        self.teacher = teacher
        self.blanks = []            # (소제목, 정답) — 학생용 정답표에 쓴다
        self._sub = ''
        z = zipfile.ZipFile(TEMPLATE)
        self.files = {n: z.read(n) for n in z.namelist()}
        self.order = [n for n in z.namelist() if n != 'Preview/PrvImage.png']
        sec = self.files['Contents/section0.xml'].decode('utf-8')
        p0 = sec.index('<hp:p ')
        self.sec_head = sec[:p0]
        run_end = sec.index('</hp:run>', sec.index('</hp:secPr>')) + len('</hp:run>')
        first_run = sec[sec.index('<hp:run', p0):run_end]
        first_run = re.sub(r'<hp:margin header="\d+" footer="\d+" gutter="0" left="\d+" right="\d+" top="\d+" '
                           r'bottom="\d+"/>',
                           '<hp:margin header="%d" footer="%d" gutter="0" left="%d" right="%d" top="%d" bottom="%d"/>'
                           % (round(5 * MM), round(8 * MM), MARGIN_LR, MARGIN_LR, round(10 * MM), round(8 * MM)),
                           first_run)
        self.first_run = first_run
        self.h = Header(self._add_font(self.files['Contents/header.xml'].decode('utf-8')))
        self.body, self.plain = [], []
        self._tbl_id = 1500000000
        self._break = False
        self._cols = 1
        self.width = TEXT_W
        self._styles()

    @staticmethod
    def _add_font(xml):
        """모든 언어 글꼴 목록에 한컴산뜻돋움을 2번으로 추가한다."""
        def add(m):
            body = m.group(2)
            info = re.search(r'<hh:typeInfo [^>]*/>', body).group(0)
            body += '<hh:font id="2" face="%s" type="TTF" isEmbedded="0">%s</hh:font>' % (FONT_NAME, info)
            return '<hh:fontface lang="%s" fontCnt="3">%s</hh:fontface>' % (m.group(1), body)
        return re.sub(r'<hh:fontface lang="(\w+)" fontCnt="2">(.*?)</hh:fontface>', add, xml, flags=re.S)

    # ── 서식 정의 ───────────────────────────────────────────
    def _styles(self):
        h = self.h
        self.C = dict(
            body=h.char(9.5), body_b=h.char(9.5, bold=True, font=DOTUM),
            cell=h.char(9), cell_b=h.char(9, bold=True, font=DOTUM), cell_u=h.char(9, underline=True),
            label=h.char(9, bold=True, font=DOTUM), head=h.char(9, bold=True, font=DOTUM),
            note=h.char(8.5, font=DOTUM, color='#333333'), small=h.char(8, font=DOTUM, color='#333333'),
            title=h.char(19, bold=True, font=DOTUM, spacing=-3), kicker=h.char(9, font=DOTUM, color='#333333'),
            sec_no=h.char(11, bold=True, font=DOTUM, color='#FFFFFF', shade='#000000'),
            sec=h.char(12.5, bold=True, font=DOTUM), sub=h.char(10.5, bold=True, font=DOTUM),
            sub_desc=h.char(8.5, font=DOTUM, color='#333333'), box_mark=h.char(10.5, bold=True, font=DOTUM),
            q_no=h.char(11, bold=True, font=DOTUM), q=h.char(9.5), q_src=h.char(8, font=DOTUM, color='#333333'),
            choice=h.char(9.5), passage=h.char(9), passage_b=h.char(9, bold=True, font=DOTUM),
            passage_u=h.char(9, underline=True), ans=h.char(9.5, bold=True, font=DOTUM), page=h.char(8.5, font=DOTUM),
            id_box=h.char(9, font=DOTUM),
            ans_cell=h.char(9, bold=True, font=DOTUM, color=RED),
            ans_body=h.char(9.5, bold=True, font=DOTUM, color=RED),
            ans_box=h.char(9, bold=True, font=DOTUM, color=RED),
            why=h.char(8.5, font=DOTUM, color=BLUE), why_b=h.char(8.5, bold=True, font=DOTUM, color=BLUE),
            teacher=h.char(9, bold=True, font=DOTUM, color='#FFFFFF', shade='#000000'),
        )
        sec_line = h.border(bottom=('0.4 mm', '#000000'))
        self.P = dict(
            body=h.para(line=160, next=300), note=h.para(line=150, next=300),
            cell=h.para('LEFT', line=150), cell_j=h.para(line=150), cell_c=h.para('CENTER', line=150),
            bullet=h.para(line=150, left=700, indent=-700),
            title=h.para('LEFT', line=120), kicker=h.para('LEFT', line=130, next=100),
            sec=h.para('LEFT', line=130, prev=1500, next=700, border=sec_line, keep_next=True,
                       border_offset=(0, 0, 0, 250)),
            sub=h.para('LEFT', line=130, prev=900, next=350, keep_next=True),
            table=h.para('LEFT', line=100, next=250),
            q=h.para(line=155, left=1250, indent=-1250, prev=1100, next=350, keep_next=True),
            choice=h.para(line=150, left=1250 + 950, indent=-950, next=80),
            choice_last=h.para(line=150, left=1250 + 950, indent=-950, next=150),
            choice_row=h.para('LEFT', line=150, left=1250, next=150),
            boxed=h.para(line=150), bogi_title=h.para('CENTER', line=130, next=100),
            page=h.para('CENTER', line=100),
        )

    # ── 기본 요소 ───────────────────────────────────────────
    @staticmethod
    def runs_xml(runs):
        out = []
        for c, t in runs:
            out.append('<hp:run charPrIDRef="%d"><hp:t>%s</hp:t></hp:run>' % (c, escape(t)) if t
                       else '<hp:run charPrIDRef="%d"/>' % c)
        return ''.join(out)

    def p_xml(self, pp, runs, page_break=False, prefix=''):
        return ('<hp:p id="0" paraPrIDRef="%d" styleIDRef="0" pageBreak="%d" columnBreak="0" merged="0">%s%s</hp:p>'
                % (pp, 1 if page_break else 0, prefix, self.runs_xml(runs)))

    def _prefix(self):
        """단 설정이 바뀌는 첫 문단에 붙일 단 정의(colPr)."""
        if getattr(self, '_pending_cols', None) is None:
            return ''
        n = self._pending_cols
        self._pending_cols = None
        line = '<hp:colLine type="SOLID" width="0.12 mm" color="#000000"/>' if n > 1 else ''
        return ('<hp:run charPrIDRef="%d"><hp:ctrl><hp:colPr id="" type="NEWSPAPER" layout="LEFT" colCount="%d" '
                'sameSz="1" sameGap="%d">%s</hp:colPr></hp:ctrl></hp:run>'
                % (self.C['body'], n, COL_GAP if n > 1 else 0, line))

    def columns(self, n):
        """이후 내용을 n단으로. 다음 문단부터 적용된다."""
        self._cols = n
        self._pending_cols = n
        self.width = COL_W if n > 1 else TEXT_W

    def page_break(self):
        self._break = True

    def _take_break(self):
        b, self._break = self._break, False
        return b

    def inline(self, t, char, bold=None, under=None):
        """**굵게**, __밑줄__, [[빈칸 정답]] 표시를 run 으로 나눈다."""
        if not isinstance(t, str):
            return t
        runs = []
        self._inline_n = getattr(self, '_inline_n', 0) + 1
        for part in re.split(r'(\*\*.+?\*\*|__.+?__|\[\[.+?\]\])', t):
            if part.startswith('[['):
                ans, _, size = part[2:-2].partition('|')
                self.blanks.append((self._sub, ans))
                if size != 'c':
                    if not hasattr(self, 'blank_src'):
                        self.blank_src = []
                    self.blank_src.append((self._inline_n, ans, t))   # 교사용 변환에서 위치 대조용
                else:
                    self.blanks.pop()          # 계산표 칸은 빈칸 정답표에 넣지 않는다
                if self.teacher:
                    ans_char = self.C['ans_body'] if char in (self.C['body'], self.C['q']) else self.C['ans_cell']
                    runs += [(ans_char, ans)] if size == 'c' else [(char, '( '), (ans_char, ans), (char, ' )')]
                else:
                    runs.append((char, '' if size == 'c' else BLANK_SHORT if size == 's' else BLANK_LONG))
            elif part.startswith('**'):
                runs.append((bold or self.C['cell_b'], part[2:-2]))
            elif part.startswith('__'):
                runs.append((under or self.C['cell_u'], part[2:-2]))
            elif part:
                runs.append((char, part))
        return runs or [(char, '')]

    def para(self, pp, runs):
        if isinstance(runs, str):
            runs = self.inline(runs, self.C['body'], self.C['body_b'])
        self.body.append(self.p_xml(self.P[pp] if isinstance(pp, str) else pp, runs, self._take_break(),
                                    self._prefix()))
        self.plain.append(''.join(t for _, t in runs))

    def table(self, widths, rows, pp='table'):
        """rows: [[cell, ...]], cell = dict(bf, paras=[(pp, runs)], va, span, size)"""
        self._tbl_id += 1
        total = sum(widths)
        trs, heights = [], []
        for r, row in enumerate(rows):
            tcs, c, row_h = [], 0, 0
            for cell in row:
                span = cell.get('span', 1)
                w = sum(widths[c:c + span])
                inner = w - 2 * CELL_PAD_X
                cell_h = 2 * CELL_PAD_Y
                for ppid, runs in cell['paras']:
                    size = cell.get('size', 9)
                    lines = max(1, math.ceil(sum(text_width(t, size) for _, t in runs) / max(inner, 1)))
                    cell_h += lines * size * 100 * 1.5
                cell_h += cell.get('raw_h', 0)
                row_h = max(row_h, round(cell_h), cell.get('min_h', 0))
                paras = ''.join(self.p_xml(ppid, runs) for ppid, runs in cell['paras']) + cell.get('raw', '')
                tcs.append((cell, paras, c, span, w))
                c += span
                self.plain.append(' '.join(''.join(t for _, t in p[1]) for p in cell['paras']))
            heights.append(row_h)
            trs.append(''.join(
                '<hp:tc name="" header="%d" hasMargin="1" protect="0" editable="0" dirty="0" borderFillIDRef="%d">'
                '<hp:subList id="" textDirection="HORIZONTAL" lineWrap="BREAK" vertAlign="%s" linkListIDRef="0" '
                'linkListNextIDRef="0" textWidth="0" textHeight="0" hasTextRef="0" hasNumRef="0">%s</hp:subList>'
                '<hp:cellAddr colAddr="%d" rowAddr="%d"/><hp:cellSpan colSpan="%d" rowSpan="1"/>'
                '<hp:cellSz width="%d" height="%d"/><hp:cellMargin left="%d" right="%d" top="%d" bottom="%d"/></hp:tc>'
                % (1 if cell.get('header') else 0, cell['bf'], cell.get('va', 'CENTER'), paras, c0, r, span, w, row_h,
                   CELL_PAD_X, CELL_PAD_X, CELL_PAD_Y, CELL_PAD_Y)
                for cell, paras, c0, span, w in tcs))
        body = ''.join('<hp:tr>%s</hp:tr>' % t for t in trs)
        tbl = ('<hp:tbl id="%d" zOrder="0" numberingType="TABLE" textWrap="TOP_AND_BOTTOM" textFlow="BOTH_SIDES" '
               'lock="0" dropcapstyle="None" pageBreak="CELL" repeatHeader="1" rowCnt="%d" colCnt="%d" cellSpacing="0" '
               'borderFillIDRef="%d" noAdjust="0"><hp:sz width="%d" widthRelTo="ABSOLUTE" height="%d" '
               'heightRelTo="ABSOLUTE" protect="0"/><hp:pos treatAsChar="0" affectLSpacing="0" flowWithText="1" '
               'allowOverlap="0" holdAnchorAndSO="0" vertRelTo="PARA" horzRelTo="COLUMN" vertAlign="TOP" '
               'horzAlign="LEFT" vertOffset="0" horzOffset="0"/><hp:outMargin left="0" right="0" top="0" bottom="0"/>'
               '<hp:inMargin left="%d" right="%d" top="%d" bottom="%d"/>%s</hp:tbl>'
               % (self._tbl_id, len(rows), len(widths), self.h.border(), total, sum(heights),
                  CELL_PAD_X, CELL_PAD_X, CELL_PAD_Y, CELL_PAD_Y, body))
        self.body.append('<hp:p id="0" paraPrIDRef="%d" styleIDRef="0" pageBreak="%d" columnBreak="0" merged="0">'
                         '%s<hp:run charPrIDRef="%d">%s<hp:t/></hp:run></hp:p>'
                         % (self.P[pp], 1 if self._take_break() else 0, self._prefix(), self.C['body'], tbl))

    # ── 표 스타일 ───────────────────────────────────────────
    def rule_bf(self, r, R, c, C, kind='body', top_bold=True):
        """위아래 굵은 선 + 안쪽 가는 회색 선 표의 칸 테두리."""
        top = LINE_BOLD if (r == 0 and top_bold) else LINE_THIN
        bottom = LINE_BOLD if r == R - 1 else LINE_THIN
        left = None if c == 0 else LINE_THIN
        right = None if c == C - 1 else LINE_THIN
        fill = {'head': FILL_HEAD, 'label': FILL_LABEL}.get(kind)
        return self.h.border(top, bottom, left, right, fill)

    def cell_paras(self, val, char, pp='cell'):
        if isinstance(val, dict):  # {'bullets': [...]}
            return [(self.P['bullet'], [(char, '· ')] + self.inline(t, char)) for t in val['bullets']]
        lines = val if isinstance(val, list) else [val]
        return [(self.P[pp], self.inline(t, char)) for t in lines]

    def grid(self, widths, head, rows, label_col=True, center=False, width=None, aligns=None):
        """head: 머리줄 글자 목록 (None 이면 없음). rows: [[label, col1, ...]]
        aligns: 칸별 정렬 'L'(왼쪽) 'C'(가운데) 'J'(양쪽) 문자열"""
        widths = self.fit(widths, width)
        pp_of = {'L': 'cell', 'C': 'cell_c', 'J': 'cell_j'}
        C = len(widths)
        R = len(rows) + (1 if head else 0)
        out = []
        if head:
            out.append([dict(bf=self.rule_bf(0, R, c, C, 'head'), header=True,
                             paras=[(self.P['cell_c'], [(self.C['head'], t)])]) for c, t in enumerate(head)])
        for i, row in enumerate(rows):
            r = i + (1 if head else 0)
            cells = []
            for c, val in enumerate(row):
                if c == 0 and label_col:
                    pp = pp_of[aligns[c]] if aligns else 'cell_c'
                    cells.append(dict(bf=self.rule_bf(r, R, c, C, 'label'), va='CENTER',
                                      paras=self.cell_paras(val, self.C['label'], pp)))
                else:
                    pp = pp_of[aligns[c]] if aligns else ('cell_c' if center else 'cell_j')
                    cells.append(dict(bf=self.rule_bf(r, R, c, C), va='CENTER',
                                      paras=self.cell_paras(val, self.C['cell'], pp)))
            out.append(cells)
        self.table(widths, out)

    def fit(self, widths, width=None):
        """폭 합계를 현재 단 폭에 맞춘다 (마지막 칸이 나머지)."""
        width = width or self.width
        total = sum(widths)
        if total == width:
            return list(widths)
        ws = [round(w * width / total) for w in widths]
        ws[-1] = width - sum(ws[:-1])
        return ws

    def box(self, lines, char=None, bold=None, under=None, width=None):
        """가는 검은 선으로 둘러싼 지문 상자"""
        char = char or self.C['passage']
        bf = self.h.border(LINE_BLACK, LINE_BLACK, LINE_BLACK, LINE_BLACK)
        paras = [(self.P['boxed'], self.inline(t, char, bold or self.C['passage_b'], under or self.C['passage_u']))
                 for t in lines]
        self.table([width or self.width], [[dict(bf=bf, va='TOP', paras=paras)]])

    # ── 학습지 부품 ─────────────────────────────────────────
    def top(self, kicker, title, intro):
        """첫 줄(구역 설정 + 쪽 번호) → 제목 띠 → 안내문"""
        footer = ('<hp:ctrl><hp:footer id="1" applyPageType="BOTH"><hp:subList id="" textDirection="HORIZONTAL" '
                  'lineWrap="BREAK" vertAlign="BOTTOM" linkListIDRef="0" linkListNextIDRef="0" textWidth="%d" '
                  'textHeight="%d" hasTextRef="0" hasNumRef="0"><hp:p id="0" paraPrIDRef="%d" styleIDRef="0" '
                  'pageBreak="0" columnBreak="0" merged="0"><hp:run charPrIDRef="%d"><hp:t>- </hp:t></hp:run>'
                  '<hp:run charPrIDRef="%d"><hp:ctrl><hp:autoNum num="1" numType="PAGE"><hp:autoNumFormat type="DIGIT" '
                  'userChar="" prefixChar="" suffixChar="" supscript="0"/></hp:autoNum></hp:ctrl></hp:run>'
                  '<hp:run charPrIDRef="%d"><hp:t> -</hp:t></hp:run></hp:p></hp:subList></hp:footer></hp:ctrl>'
                  % (TEXT_W, round(8 * MM), self.P['page'], self.C['page'], self.C['page'], self.C['page']))
        self.body.append('<hp:p id="0" paraPrIDRef="%d" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0">%s%s'
                         '</hp:p>' % (self.P['kicker'], self.first_run.replace('</hp:run>', footer + '</hp:run>', 1),
                                      self.runs_xml([(self.C['kicker'], kicker)])))
        self.plain.append(kicker)
        # 제목 띠: 위 굵은 선, 아래 가는 선 / 오른쪽 학번·이름 칸
        bf_t = self.h.border(('0.7 mm', '#000000'), ('0.25 mm', '#000000'), None, None)
        bf_id = self.h.border(('0.7 mm', '#000000'), ('0.25 mm', '#000000'), LINE_THIN, None)
        w_id = round(52 * MM)
        title_runs = [(self.C['title'], title)]
        if self.teacher:
            title_runs.append((self.C['title'], '  '))
            title_runs.append((self.C['ans_body'], '[교사용]'))
        self.table([TEXT_W - w_id, w_id], [[
            dict(bf=bf_t, va='CENTER', size=19, paras=[(self.P['title'], title_runs)]),
            dict(bf=bf_id, va='CENTER', paras=[(self.P['cell'], [(self.C['id_box'], '학번 :')]),
                                               (self.P['cell'], [(self.C['id_box'], '이름 :')])]),
        ]])
        if intro:
            self.para('note', [(self.C['note'], intro)])

    def section(self, num, title, page_break=False, columns=None):
        if page_break:
            self.page_break()
        if columns is not None and columns != self._cols:
            self.columns(columns)
        self.para('sec', [(self.C['sec_no'], ' %s ' % num), (self.C['sec'], '  ' + title)])

    def sub(self, title, desc=''):
        self._sub = title
        runs = [(self.C['box_mark'], '■ '), (self.C['sub'], title)]
        if desc:
            runs.append((self.C['sub_desc'], '   ' + desc))
        self.para('sub', runs)

    def blank_key(self):
        """빈칸 정답을 소제목별로 묶은 표 행"""
        rows = []
        for sub, ans in self.blanks:
            if rows and rows[-1][0] == sub:
                rows[-1][1].append(ans)
            else:
                rows.append([sub, [ans]])
        return [[sub, ' · '.join(a)] for sub, a in rows]

    def note(self, text):
        self.para('note', self.inline(text, self.C['note'], self.C['note']))

    def numbered(self, items, num_w=2000):
        R = len(items)
        rows = []
        for i, (title, desc) in enumerate(items):
            rows.append([
                dict(bf=self.rule_bf(i, R, 0, 2, 'label'), va='CENTER',
                     paras=[(self.P['cell_c'], [(self.C['label'], str(i + 1))])]),
                dict(bf=self.rule_bf(i, R, 1, 2), va='CENTER',
                     paras=[(self.P['cell'], [(self.C['cell_b'], title)]),
                            (self.P['cell_j'], self.inline(desc, self.C['cell']))])])
        self.table(self.fit([num_w, self.width - num_w]), rows)

    def quiz(self, items, widths, answer='(          )', answers=None, notes=None):
        """번호 | 문장 | 답칸. 교사용이면 답칸에 정답, 문장 아래에 해설(notes)."""
        widths = self.fit(widths)
        R = len(items)
        rows = []
        for i, text in enumerate(items):
            text_paras = [(self.P['cell_j'], self.inline(text, self.C['cell']))]
            ans_runs = [(self.C['cell'], answer)]
            if self.teacher and answers:
                ans_runs = [(self.C['ans_cell'], answers[i])]
                if notes and notes[i]:
                    text_paras.append((self.P['cell_j'], [(self.C['why_b'], '→ '), (self.C['why'], notes[i])]))
            rows.append([
                dict(bf=self.rule_bf(i, R, 0, 3, 'label'), paras=[(self.P['cell_c'], [(self.C['label'], str(i + 1))])]),
                dict(bf=self.rule_bf(i, R, 1, 3), paras=text_paras),
                dict(bf=self.rule_bf(i, R, 2, 3), paras=[(self.P['cell_c'], ans_runs)]),
            ])
        self.table(widths, rows)

    def answers(self, items, widths):
        """번호 | 정답 | 해설"""
        widths = self.fit(widths)
        R = len(items)
        rows = []
        for i, (ans, why) in enumerate(items):
            rows.append([
                dict(bf=self.rule_bf(i, R, 0, 3, 'label'), paras=[(self.P['cell_c'], [(self.C['label'], str(i + 1))])]),
                dict(bf=self.rule_bf(i, R, 1, 3), paras=[(self.P['cell_c'], [(self.C['ans'], ans)])]),
                dict(bf=self.rule_bf(i, R, 2, 3), paras=[(self.P['cell_j'], self.inline(why, self.C['cell']))]),
            ])
        self.table(widths, rows)

    def question(self, n, q, circled='①②③④⑤', answer_box=True):
        """기출 한 문항 (현재 단 폭에 맞춤)"""
        self.para('q', [(self.C['q_no'], '%d.  ' % n)] + self.inline(q['stem'], self.C['q'], self.C['body_b'])
                  + [(self.C['q_src'], '  [%s]' % q['src'])])
        indent = 1250
        w = self.width - indent
        if q.get('box'):
            self._indented(lambda: self.box(q['box'], width=w))
        if q.get('grid'):
            head, rows = q['grid']
            n_col = len(head)
            if q.get('grid_w'):
                widths = q['grid_w']
            elif q.get('grid_even'):
                widths = [w // n_col] * n_col
            else:
                other = 1900 if n_col > 4 else 3600
                widths = [w - other * (n_col - 1)] + [other] * (n_col - 1)
            self._indented(lambda: self.grid(widths, head, rows, label_col=False, center=not q.get('grid_even') or q.get('grid_center', False),
                                             width=w))
        if q.get('box_after'):
            self._indented(lambda: self.box(q['box_after'], width=w))
        if q.get('bogi'):
            bf = self.h.border(LINE_BLACK, LINE_BLACK, LINE_BLACK, LINE_BLACK)
            paras = [(self.P['bogi_title'], [(self.C['passage_b'], '< 보 기 >')])]
            paras += [(self.P['boxed'], self.inline(t, self.C['passage'])) for t in q['bogi']]
            self._indented(lambda: self.table([w], [[dict(bf=bf, va='TOP', paras=paras)]]))
        ch = q['choices']
        self._choices(ch, w, circled)
        if self.teacher and q.get('ans') and answer_box:
            bf = self.h.border(LINE_BLACK, LINE_BLACK, LINE_BLACK, LINE_BLACK, FILL_LABEL)
            paras = [(self.P['boxed'], [(self.C['ans_box'], '정답  %s' % q['ans'])]),
                     (self.P['boxed'], self.inline(q.get('why', ''), self.C['why'], self.C['why_b']))]
            self._indented(lambda: self.table([w], [[dict(bf=bf, va='TOP', paras=paras)]]))

    def _choices(self, ch, w, circled):
        if max(len(c) for c in ch) <= 6:   # 짧은 선지는 한 줄에, 넘치면 3개·2개로 나눔
            items = ['%s %s' % (circled[k], c) for k, c in enumerate(ch)]
            gap = '    '
            if text_width(gap.join(items), 9.5) > w:
                self.para('choice', [(self.C['choice'], gap.join(items[:3]))])
                self.para('choice_row', [(self.C['choice'], gap.join(items[3:]))])
            else:
                self.para('choice_row', [(self.C['choice'], gap.join(items))])
            return
        for k, c in enumerate(ch):
            self.para('choice_last' if k == len(ch) - 1 else 'choice',
                      [(self.C['choice'], '%s ' % circled[k])] + self.inline(c, self.C['choice']))

    # ── 문제 | 풀이 칸 ─────────────────────────────────────
    def capture(self, fn, width):
        """fn 이 만드는 문단들을 본문 대신 문자열로 받아 온다 (표 칸 안에 넣을 때)."""
        start, old_w = len(self.body), self.width
        self.width = width
        fn()
        xml = ''.join(self.body[start:])
        del self.body[start:]
        self.width = old_w
        return xml

    def problem(self, left_fn, solution=None, answer=None, sheet_fn=None, ratio=0.6, min_h=0):
        """왼쪽 문제 | 오른쪽 풀이 칸 (1줄 표 하나 = 1문항).
        left_fn   : 왼쪽 칸 내용을 그리는 함수 (question 등)
        solution  : 교사용 풀이 줄 목록 (파랑), answer: 교사용 정답 (빨강)
        sheet_fn  : 풀이 칸에 넣을 빈 계산표 등 (학생·교사 공통, 교사용은 정답이 채워짐)
        """
        lw = round(self.width * ratio)
        rw = self.width - lw
        left = self.capture(left_fn, lw - 2 * CELL_PAD_X)
        right_paras = [(self.P['cell'], [(self.C['why_b'] if self.teacher else self.C['small'], '풀이')])]
        right_raw = self.capture(sheet_fn, rw - 2 * CELL_PAD_X) if sheet_fn else ''
        if self.teacher:
            extra = [(self.P['cell_j'], self.inline(line, self.C['why'], self.C['why_b'])) for line in (solution or [])]
            if answer:
                extra.append((self.P['cell'], [(self.C['ans_box'], '정답  %s' % answer)]))
            right_raw += ''.join(self.p_xml(pp, runs) for pp, runs in extra)
        top = LINE_BLACK
        bf_l = self.h.border(top, LINE_THIN, None, LINE_THIN)
        bf_r = self.h.border(top, LINE_THIN, LINE_THIN, None)
        est = left.count('<hp:p ') * 1450
        self.table([lw, rw], [[dict(bf=bf_l, va='TOP', paras=[], raw=left, raw_h=est, min_h=min_h),
                               dict(bf=bf_r, va='TOP', paras=right_paras, raw=right_raw)]])

    def calc_sheet(self, rows, head=('대안', '편익', '명시적 비용', '순편익', '암묵적 비용', '기회비용', '판단')):
        """기회비용 계산표. rows 칸에 [[정답]]을 쓰면 학생용은 빈칸, 교사용은 정답."""
        n = len(head)
        first = max(3800, self.width // (n + 1))
        widths = [first] + [(self.width - first) // (n - 1)] * (n - 1)
        widths[-1] = self.width - sum(widths[:-1])
        cells = [[r[0]] + [self._calc_cell(v) for v in r[1:]] for r in rows]
        self.grid(widths, list(head), cells, center=True, width=self.width)

    def _calc_cell(self, v):
        if isinstance(v, str) and v.startswith('?'):
            return '[[%s|c]]' % v[1:]
        return v

    def _indented(self, fn):
        """문항 안의 표·상자를 번호 폭만큼 들여 놓는다."""
        start = len(self.body)
        fn()
        for i in range(start, len(self.body)):
            self.body[i] = self.body[i].replace('horzOffset="0"/>', 'horzOffset="1250"/>', 1)

    # ── 저장 ───────────────────────────────────────────────
    def save(self, path):
        sec = self.sec_head + ''.join(self.body) + '</hs:sec>'
        files = dict(self.files)
        files['Contents/section0.xml'] = sec.encode('utf-8')
        files['Contents/header.xml'] = self.h.xml.encode('utf-8')
        files['Preview/PrvText.txt'] = '\r\n'.join(self.plain)[:1000].encode('utf-8')
        with zipfile.ZipFile(path, 'w') as z:
            for n in self.order:
                comp = zipfile.ZIP_STORED if n == 'mimetype' else zipfile.ZIP_DEFLATED
                z.writestr(zipfile.ZipInfo(n, (1980, 1, 1, 0, 0, 0)), files[n], compress_type=comp)


if __name__ == '__main__':
    out, mod = sys.argv[1], sys.argv[2]
    sheet = Sheet(teacher='--teacher' in sys.argv[3:])
    importlib.import_module(mod).build(sheet)
    sheet.save(out)
    print('saved', out)
