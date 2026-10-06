"""학습지 HWPX 생성기 — 「기본권의 유형」 학습지의 서식(header.xml)을 그대로 쓰고 본문만 새로 만든다.

usage: python3 worksheet_hwpx.py template.hwpx out.hwpx module
  template.hwpx : 서식을 가져올 기존 학습지 (기본권의 유형)
  module        : 내용 모듈 이름 (예: ws_economy1) — build(doc) 함수를 가진 .py
"""
import importlib
import re
import sys
import zipfile
from xml.sax.saxutils import escape

# ── 서식 ID (기본권의 유형 학습지 header.xml 기준) ─────────────────────────
# 글자: 12 회색 굵게 8pt / 13 제목 22pt / 14 부제 12pt / 15 안내문 / 16 소제목 12pt 굵게
#       17 흰색 굵게 8pt / 18 본문 8pt / 21 회색 8pt / 22 굵게 8.5pt / 27 본문 8.5pt / 30 진회색 8pt
#       19·20 파랑, 23·24 금색, 25·26 빨강, 28·32 초록, 29 보라 (11pt / 9.5pt 굵게)
# 문단: 3 머리말·제목 / 4 부제(밑줄) / 5 안내문 / 6 소제목(밑줄) / 7 가운데 / 8 왼쪽
#       9·10·11 상자 도식 / 12·16·18·19·20 색 막대 제목(파랑·초록·금색·보라·빨강)
#       13 본문(아래 5) / 14 – 글머리 / 17 위 8 아래 4 / 21 여백 없음 / 22 아래 6 / 23 위아래 5
COLORS = {  # 이름: (머리줄 칸 테두리, 큰 글자, 중간 글자, 색 막대 문단)
    'blue': (5, 19, 20, 12), 'green': (15, 28, 32, 16), 'gold': (16, 23, 24, 18),
    'purple': (17, 29, None, 19), 'red': (None, 25, 26, 20),
}
HEX = {'blue': '#2B5FA8', 'green': '#1D7A5C', 'gold': '#A8781A', 'purple': '#6A4A9C', 'red': '#B04A2C'}
TEXT_W = 49530


class Header:
    """header.xml 에 테두리/글자 모양을 복제해 추가한다."""

    def __init__(self, xml):
        self.xml = xml

    def _clone(self, tag, group, base_id, edit):
        m = re.search(r'<hh:%s id="%d".*?</hh:%s>' % (tag, base_id, tag), self.xml, re.S)
        cnt_m = re.search(r'<hh:%s itemCnt="(\d+)"' % group, self.xml)
        new_id = max(int(i) for i in re.findall(r'<hh:%s id="(\d+)"' % tag, self.xml)) + 1
        el = edit(re.sub(r'id="%d"' % base_id, 'id="%d"' % new_id, m.group(0), count=1))
        end = self.xml.index('</hh:%s>' % group)
        self.xml = self.xml[:end] + el + self.xml[end:]
        self.xml = self.xml.replace(cnt_m.group(0), '<hh:%s itemCnt="%d"' % (group, int(cnt_m.group(1)) + 1), 1)
        return new_id

    def border(self, base_id, fill=None, right=None):
        def edit(el):
            if fill:
                el = re.sub(r'faceColor="[^"]+"', 'faceColor="%s"' % fill, el)
            if right:
                el = re.sub(r'(<hh:rightBorder [^>]*color=")[^"]+"', r'\g<1>%s"' % right, el)
            return el
        return self._clone('borderFill', 'borderFills', base_id, edit)

    def char(self, base_id, height=None, color=None, underline=False):
        def edit(el):
            if underline:
                el = el.replace('<hh:underline type="NONE" shape="SOLID" color="#000000"/>',
                                '<hh:underline type="BOTTOM" shape="SOLID" color="#111C27"/>')
            if height:
                el = re.sub(r'height="\d+"', 'height="%d"' % height, el, count=1)
            if color:
                el = re.sub(r'textColor="[^"]+"', 'textColor="%s"' % color, el, count=1)
            return el
        return self._clone('charPr', 'charProperties', base_id, edit)


class Doc:
    def __init__(self, template):
        z = zipfile.ZipFile(template)
        self.files = {n: z.read(n) for n in z.namelist()}
        self.order = z.namelist()
        sec = self.files['Contents/section0.xml'].decode('utf-8')
        # 첫 문단의 구역 설정(secPr)·단 설정 run 을 그대로 재사용
        p0 = sec.index('<hp:p ')
        run_end = sec.index('</hp:run>', sec.index('</hp:secPr>')) + len('</hp:run>')
        self.sec_head = sec[:p0]
        self.first_run = sec[sec.index('<hp:run', p0):run_end]
        fs = sec.index('<hp:ctrl><hp:footer')
        self.footer = sec[fs:sec.index('</hp:ctrl>', sec.index('</hp:footer>', fs)) + len('</hp:ctrl>')]
        self.header = Header(self.files['Contents/header.xml'].decode('utf-8'))
        self.body = []
        self.plain = []
        self._tbl_id = 1300000000
        self._break = False
        h = self.header
        # 기존에 없는 색 조합 추가
        self.bf = {
            'head_purple_last': h.border(17, right='#D8DFE6'),
            'head_red_mid': h.border(16, fill='#B04A2C'),
            'head_green_last': h.border(6, fill='#1D7A5C'),
            'head_gold_last': h.border(6, fill='#A8781A'),
            'head_blue_last': h.border(6, fill='#2B5FA8'),
            'box_mid': 18, 'box_first': 11, 'box_last': 19,
        }
        self.c_purple_mid = h.char(29, height=950)
        self.c_under = h.char(27, underline=True)

    # ── 기본 요소 ───────────────────────────────────────────────
    @staticmethod
    def runs_xml(runs):
        out = []
        for c, t in runs:
            out.append('<hp:run charPrIDRef="%d"><hp:t>%s</hp:t></hp:run>' % (c, escape(t)) if t
                       else '<hp:run charPrIDRef="%d"/>' % c)
        return ''.join(out)

    def p_xml(self, pp, runs, style=0, page_break=False):
        return ('<hp:p id="0" paraPrIDRef="%d" styleIDRef="%d" pageBreak="%d" columnBreak="0" merged="0">%s</hp:p>'
                % (pp, style, 1 if page_break else 0, self.runs_xml(runs)))

    def para(self, pp, runs, style=0):
        if isinstance(runs, str):
            runs = [(27, runs)]
        self.body.append(self.p_xml(pp, runs, style, self._take_break()))
        self.plain.append(''.join(t for _, t in runs))

    def _take_break(self):
        b, self._break = self._break, False
        return b

    def page_break(self):
        self._break = True

    def table(self, widths, rows, pp=13, va=None):
        """rows: [[cell, ...], ...], cell = dict(bf, paras=[(pp, runs, style)], va)"""
        self._tbl_id += 1
        total = sum(widths)
        trs = []
        for r, row in enumerate(rows):
            tcs = []
            c = 0
            for cell in row:
                span = cell.get('span', 1)
                w = sum(widths[c:c + span])
                paras = ''.join(self.p_xml(p[0], p[1], p[2] if len(p) > 2 else 0) for p in cell['paras'])
                tcs.append(
                    '<hp:tc name="" header="%d" hasMargin="1" protect="0" editable="0" dirty="0" borderFillIDRef="%d">'
                    '<hp:subList id="" textDirection="HORIZONTAL" lineWrap="BREAK" vertAlign="%s" linkListIDRef="0" '
                    'linkListNextIDRef="0" textWidth="0" textHeight="0" hasTextRef="0" hasNumRef="0">%s</hp:subList>'
                    '<hp:cellAddr colAddr="%d" rowAddr="%d"/><hp:cellSpan colSpan="%d" rowSpan="1"/>'
                    '<hp:cellSz width="%d" height="0"/><hp:cellMargin left="450" right="450" top="350" bottom="350"/></hp:tc>'
                    % (1 if cell.get('header') else 0, cell['bf'], cell.get('va', va or 'TOP'), paras, c, r, span, w))
                c += span
                self.plain.append(' '.join(''.join(t for _, t in p[1]) for p in cell['paras']))
            trs.append('<hp:tr>%s</hp:tr>' % ''.join(tcs))
        tbl = ('<hp:tbl id="%d" zOrder="0" numberingType="TABLE" textWrap="TOP_AND_BOTTOM" textFlow="BOTH_SIDES" '
               'lock="0" dropcapstyle="None" pageBreak="CELL" repeatHeader="1" rowCnt="%d" colCnt="%d" cellSpacing="0" '
               'borderFillIDRef="4" noAdjust="0"><hp:sz width="%d" widthRelTo="ABSOLUTE" height="0" heightRelTo="ABSOLUTE" '
               'protect="0"/><hp:pos treatAsChar="0" affectLSpacing="0" flowWithText="1" allowOverlap="0" '
               'holdAnchorAndSO="0" vertRelTo="PARA" horzRelTo="COLUMN" vertAlign="TOP" horzAlign="LEFT" vertOffset="0" '
               'horzOffset="0"/><hp:outMargin left="0" right="0" top="0" bottom="0"/>'
               '<hp:inMargin left="540" right="540" top="0" bottom="0"/>%s</hp:tbl>'
               % (self._tbl_id, len(rows), len(widths), total, ''.join(trs)))
        self.body.append('<hp:p id="0" paraPrIDRef="%d" styleIDRef="0" pageBreak="%d" columnBreak="0" merged="0">'
                         '<hp:run charPrIDRef="12">%s<hp:t/></hp:run></hp:p>' % (pp, 1 if self._take_break() else 0, tbl))

    # ── 학습지 부품 ─────────────────────────────────────────────
    def top(self, header_text, title, subtitle, intro):
        self.body.append('<hp:p id="0" paraPrIDRef="3" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0">'
                         + self.first_run.replace('</hp:run>', self.footer + '</hp:run>', 1)
                         + self.runs_xml([(0, '고촌고 1학년 '), (12, header_text)]) + '</hp:p>')
        self.plain.append('고촌고 1학년 ' + header_text)
        self.para(3, [(13, title)])
        self.para(4, [(14, subtitle)])
        self.para(5, [(15, intro)])

    def section(self, num, title, page_break=False):
        if page_break:
            self.page_break()
        self.para(6, [(12, num + '  '), (16, title)])

    def note(self, text):
        self.para(22, [(21, text)])

    def color_head(self, color, name, sub=''):
        _, big, _, pp = COLORS[color]
        self.para(pp, [(big, name), (21, '   ' + sub)] if sub else [(big, name)])

    def grid(self, widths, head, rows, head_colors=None, label_col=True, cell_char=18, cell_pp=8, head_pp=7):
        """비교표. head: 머리줄 글자들(None 이면 머리줄 없음), rows: [[label, col1, ...], ...]
        각 칸 내용은 문자열 또는 문자열 목록(여러 줄) 또는 [(char, text)] run 목록."""
        n = len(widths)
        R = len(rows) + (1 if head else 0)
        out = []
        if head:
            cells = []
            for c, text in enumerate(head):
                if c == 0 and label_col:
                    bf = 14 if n > 1 else 25
                else:
                    color = (head_colors or [None] * n)[c]
                    last = c == n - 1
                    bf = self.head_bf(color, last)
                cells.append(dict(bf=bf, paras=[(head_pp, [(17, text)])], header=True, va='CENTER'))
            out.append(cells)
        for i, row in enumerate(rows):
            r = i + (1 if head else 0)
            first, last_row = r == 0, r == R - 1
            cells = []
            for c, val in enumerate(row):
                last_col = c == n - 1
                if c == 0 and label_col:
                    bf = 25 if first else (8 if last_row else 7)
                    paras = self.cell_paras(val, 12, cell_pp)
                else:
                    if first:
                        bf = 22 if last_col else 31
                    elif last_row:
                        bf = 13 if last_col else 12
                    else:
                        bf = 10 if last_col else 9
                    paras = self.cell_paras(val, cell_char, cell_pp)
                cells.append(dict(bf=bf, paras=paras))
            out.append(cells)
        self.table(widths, out)

    def head_bf(self, color, last):
        if color is None:
            return 24 if last else 23
        mid = {'blue': 5, 'green': 15, 'gold': 16, 'purple': 17, 'red': self.bf['head_red_mid']}
        lst = {'blue': self.bf['head_blue_last'], 'green': self.bf['head_green_last'],
               'gold': self.bf['head_gold_last'], 'purple': self.bf['head_purple_last'], 'red': 6}
        return (lst if last else mid)[color]

    def cell_paras(self, val, char, pp):
        if isinstance(val, dict):  # {'bullets': [...]} → – 글머리
            return [(14, self.inline(t, char), 11) for t in val['bullets']]
        lines = val if isinstance(val, list) else [val]
        return [(pp, self.inline(t, char)) for t in lines]

    def inline(self, t, char):
        """문자열 안의 **굵게**, __밑줄__ 표시를 run 으로 나눈다."""
        if not isinstance(t, str):
            return t
        runs = []
        for part in re.split(r'(\*\*.+?\*\*|__.+?__)', t):
            if part.startswith('**'):
                runs.append((22, part[2:-2]))
            elif part.startswith('__'):
                runs.append((self.c_under, part[2:-2]))
            elif part:
                runs.append((char, part))
        return runs or [(char, '')]

    def boxes(self, items):
        """상자 도식: items = [(color, big, mid, desc, result)]"""
        n = len(items)
        w = [TEXT_W // n] * n
        w[-1] = TEXT_W - sum(w[:-1])
        cells = []
        for i, (color, big, mid, desc, result) in enumerate(items):
            _, cbig, cmid, _ = COLORS[color]
            cmid = cmid or self.c_purple_mid
            bf = self.bf['box_first'] if i == 0 else (self.bf['box_last'] if i == n - 1 else self.bf['box_mid'])
            cells.append(dict(bf=bf, paras=[(9, [(cbig, big)]), (10, [(cmid, mid)]), (10, [(21, desc)]),
                                            (11, [(22, result)])]))
        self.table(w, [cells])

    def numbered(self, items, width_num=2600):
        """번호 + 굵은 제목 + 설명 목록 (틀리기 쉬운 지점)"""
        rows = []
        R = len(items)
        for i, (title, desc) in enumerate(items):
            last = i == R - 1
            bf_num = 14 if i == 0 else (30 if last else 29)
            bf_txt = 22 if i == 0 else (13 if last else 10)
            rows.append([dict(bf=bf_num, va='CENTER', paras=[(7, [(17, str(i + 1))])]),
                         dict(bf=bf_txt, paras=[(30, [(22, title)]), (31, [(30, desc)])])])
        self.table([width_num, TEXT_W - width_num], rows)

    def quiz_rows(self, items, widths, right_text='(          )', right_pp=36, right_char=18):
        """번호 | 문장 | 답칸"""
        rows = []
        R = len(items)
        for i, text in enumerate(items):
            first, last = i == 0, i == R - 1
            rows.append([
                dict(bf=25 if first else (8 if last else 7), va='CENTER', paras=[(35, [(12, str(i + 1))])]),
                dict(bf=31 if first else (12 if last else 9), paras=[(34, self.inline(text, 27))]),
                dict(bf=22 if first else (13 if last else 10), va='CENTER', paras=[(right_pp, [(right_char, right_text)])]),
            ])
        self.table(widths, rows)

    def answer_rows(self, items, widths):
        """번호 | 정답(O 초록 / X 빨강 / 그 밖) | 해설"""
        rows = []
        R = len(items)
        for i, (ans, why) in enumerate(items):
            first, last = i == 0, i == R - 1
            c = 32 if ans == 'O' else (26 if ans == 'X' else 22)
            rows.append([
                dict(bf=25 if first else (8 if last else 7), va='CENTER', paras=[(7, [(12, str(i + 1))])]),
                dict(bf=31 if first else (12 if last else 9), va='CENTER', paras=[(7, [(c, ans)])]),
                dict(bf=22 if first else (13 if last else 10), paras=[(8, self.inline(why, 18))]),
            ])
        self.table(widths, rows)

    def box(self, lines, char=27, pp=8):
        """회색 바탕 지문 상자"""
        self.table([TEXT_W], [[dict(bf=25, paras=[(pp, self.inline(t, char)) for t in lines])]])

    # ── 저장 ───────────────────────────────────────────────────
    def save(self, path):
        sec = self.sec_head + ''.join(self.body) + '</hs:sec>'
        files = dict(self.files)
        files['Contents/section0.xml'] = sec.encode('utf-8')
        files['Contents/header.xml'] = self.header.xml.encode('utf-8')
        files['Preview/PrvText.txt'] = '\r\n'.join(self.plain)[:2000].encode('utf-16-le') \
            if self._prv_utf16() else '\r\n'.join(self.plain)[:2000].encode('utf-8')
        order = [n for n in self.order if n != 'Preview/PrvImage.png']
        hpf = files['Contents/content.hpf'].decode('utf-8')
        hpf = re.sub(r'<opf:item id="image\d*"[^>]*PrvImage[^>]*/>', '', hpf)
        files['Contents/content.hpf'] = hpf.encode('utf-8')
        with zipfile.ZipFile(path, 'w') as z:
            for n in order:
                comp = zipfile.ZIP_STORED if n == 'mimetype' else zipfile.ZIP_DEFLATED
                z.writestr(zipfile.ZipInfo(n, (1980, 1, 1, 0, 0, 0)), files[n], compress_type=comp)

    def _prv_utf16(self):
        raw = self.files.get('Preview/PrvText.txt', b'')
        return raw[:2] in (b'\xff\xfe', b'\xfe\xff') or (len(raw) > 1 and raw[1:2] == b'\x00')


if __name__ == '__main__':
    template, out, mod = sys.argv[1], sys.argv[2], sys.argv[3]
    doc = Doc(template)
    importlib.import_module(mod).build(doc)
    doc.save(out)
    print('saved', out)
