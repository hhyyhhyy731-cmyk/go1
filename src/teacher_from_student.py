"""한글에서 손본 학생용 학습지(HWPX)에 정답을 넣어 교사용을 만든다. 학생용의 서식은 그대로 둔다.

usage: python3 teacher_from_student.py 학생용.hwpx module 교사용.hwpx
  module : 내용 모듈 (예: ws_economy1) — 빈칸 정답([[정답]]), OX, SORT, EXAMS 를 읽는다

넣는 것
  · 개념 정리 빈칸 → ( 정답 ) 빨간 굵은 글씨
  · OX 답칸 → O / X 빨간 굵은 글씨, 문장 아래에 파란 해설
  · 판별 답칸 → 정답 빨간 굵은 글씨
  · 기출 → 마지막 선지 아래에 회색 상자(정답 빨강, 해설 파랑)
  · 제목 옆 [교사용]
"""
import copy
import importlib
import re
import sys
import zipfile

from lxml import etree

from sheet_hwpx import Sheet

RED = '#D00000'
BLUE = '#1F4E9A'
HP = 'http://www.hancom.co.kr/hwpml/2011/paragraph'
NS = {'hp': HP}
BLANK = re.compile(r'\(\s{3,}\)')


def q(tag):
    return '{%s}%s' % (HP, tag)


class Header:
    def __init__(self, xml):
        self.xml = xml
        self.cache = {}

    def _clone(self, tag, group, base_id, edit):
        m = re.search(r'<hh:%s id="%s".*?</hh:%s>' % (tag, base_id, tag), self.xml, re.S)
        new_id = max(int(i) for i in re.findall(r'<hh:%s id="(\d+)"' % tag, self.xml)) + 1
        el = edit(re.sub(r'id="%s"' % base_id, 'id="%d"' % new_id, m.group(0), count=1))
        end = self.xml.index('</hh:%s>' % group)
        self.xml = self.xml[:end] + el + self.xml[end:]
        cnt = re.search(r'<hh:%s itemCnt="(\d+)"' % group, self.xml)
        self.xml = self.xml.replace(cnt.group(0), '<hh:%s itemCnt="%d"' % (group, int(cnt.group(1)) + 1), 1)
        return str(new_id)

    def char(self, base_id, color, bold=False, smaller=0, plain=False):
        key = ('c', base_id, color, bold, smaller, plain)
        if key not in self.cache:
            def edit(el):
                if plain:
                    el = el.replace('<hh:bold/>', '')
                el = re.sub(r'textColor="[^"]+"', 'textColor="%s"' % color, el, count=1)
                if smaller:
                    el = re.sub(r'height="(\d+)"', lambda m: 'height="%d"' % (int(m.group(1)) - smaller), el, count=1)
                if bold and '<hh:bold' not in el:
                    el = el.replace('<hh:underline', '<hh:bold/><hh:underline', 1)
                return el
            self.cache[key] = self._clone('charPr', 'charProperties', base_id, edit)
        return self.cache[key]

    def fill(self, base_id, color):
        key = ('b', base_id, color)
        if key not in self.cache:
            self.cache[key] = self._clone('borderFill', 'borderFills', base_id,
                                          lambda el: re.sub(r'faceColor="[^"]+"', 'faceColor="%s"' % color, el))
        return self.cache[key]


def text_of(el):
    return ''.join(el.xpath('.//hp:t/text()', namespaces=NS))


def own_text(p):
    """문단 자신의 글자 (안에 든 표의 글자는 뺀다)"""
    return ''.join(t.text or '' for r in p.findall(q('run')) for t in r.findall(q('t')))


def make_run(char, text):
    r = etree.Element(q('run'), charPrIDRef=char)
    etree.SubElement(r, q('t')).text = text
    return r


def split_run(t, pieces):
    """hp:t 하나를 [(charPrIDRef 또는 None=원래 글자, text)] 조각들로 나눠 run 여러 개로 바꾼다."""
    run = t.getparent()
    base = run.get('charPrIDRef')
    parent = run.getparent()
    idx = parent.index(run)
    children = list(run)
    k = children.index(t)
    before, after = children[:k], children[k + 1:]
    new = []
    if before:
        r0 = etree.Element(q('run'), dict(run.attrib))
        r0.extend(before)
        new.append(r0)
    for char, text in pieces:
        if text:
            new.append(make_run(char or base, text))
    if after:
        r2 = etree.Element(q('run'), dict(run.attrib))
        r2.extend(after)
        new.append(r2)
    parent.remove(run)
    for j, r in enumerate(new):
        parent.insert(idx + j, r)


def main(student, mod_name, out):
    mod = importlib.import_module(mod_name)
    probe = Sheet()
    mod.build(probe)
    blank_answers = [a for _, a in probe.blanks]
    ox = [(s, a, w) for s, a, w in mod.OX]
    sort = mod.SORT
    exams = mod.EXAMS

    z = zipfile.ZipFile(student)
    files = {n: z.read(n) for n in z.namelist()}
    h = Header(files['Contents/header.xml'].decode('utf-8'))
    root = etree.fromstring(files['Contents/section0.xml'])

    # 저장된 줄 배치 정보는 지운다 — 글자가 바뀌면 한글이 다시 계산한다
    for ls in root.iter(q('linesegarray')):
        ls.getparent().remove(ls)

    # 1) 빈칸: 개념 정리 → OX 답칸 순서
    texts = [t for t in root.iter(q('t')) if t.text and BLANK.search(t.text)]
    n_blank = sum(len(BLANK.findall(t.text)) for t in texts)
    if n_blank != len(blank_answers) + len(ox):
        sys.exit('빈칸 수가 맞지 않습니다: 학습지 %d개, 정답 %d개 + OX %d개'
                 % (n_blank, len(blank_answers), len(ox)))
    answers = iter(blank_answers + [a for _, a, _ in ox])
    count = 0
    for t in texts:
        base = t.getparent().get('charPrIDRef')
        red = h.char(base, RED, bold=True)
        pieces, pos = [], 0
        for m in BLANK.finditer(t.text):
            ans = next(answers)
            pieces.append((None, t.text[pos:m.start()]))
            if count < len(blank_answers):
                pieces += [(None, '( '), (red, ans), (None, ' )')]
            else:
                pieces.append((red, ans))
            pos = m.end()
            count += 1
        pieces.append((None, t.text[pos:]))
        split_run(t, pieces)

    # 2) OX 해설, 판별 정답: 문장이 든 칸을 찾아 같은 줄의 칸을 채운다
    cells = list(root.iter(q('tc')))
    ox_why = {s: w for s, _, w in ox}
    sort_ans = dict(sort)
    for tc in cells:
        txt = text_of(tc).strip()
        if txt in ox_why:
            p = tc.find('.//hp:p', NS)
            base = p.find(q('run')).get('charPrIDRef')
            np = copy.deepcopy(p)
            for r in np.findall(q('run')):
                np.remove(r)
            np.append(make_run(h.char(base, BLUE, smaller=50), '→ ' + ox_why[txt]))
            p.addnext(np)
        elif txt in sort_ans:
            row = tc.getparent()
            ans_tc = row.findall(q('tc'))[-1]
            p = ans_tc.find('.//hp:p', NS)
            run = p.find(q('run'))
            base = run.get('charPrIDRef') if run is not None else tc.find('.//hp:run', NS).get('charPrIDRef')
            for r in p.findall(q('run')):
                p.remove(r)
            p.append(make_run(h.char(base, RED, bold=True), sort_ans[txt]))

    # 3) 기출: 문항 문단을 찾아 마지막 선지 아래에 정답 상자
    top = root.findall(q('p'))
    starts = []
    for i, ex in enumerate(exams):
        key = re.sub(r'\*\*|__', '', ex['stem'])[:14]
        for j, p in enumerate(top):
            if re.match(r'\s*%d\.' % (i + 1), own_text(p)) and key in own_text(p).replace('  ', ' '):
                starts.append(j)
                break
        else:
            sys.exit('%d번 문항을 찾지 못했습니다' % (i + 1))
    # 상자 틀: 1번 문항의 지문 상자(1칸 표)를 복사해 쓴다
    tmpl = None
    for p in top[starts[0]:starts[1]]:
        tbl = p.find('.//hp:tbl', NS)
        if tbl is not None and tbl.get('rowCnt') == '1' and tbl.get('colCnt') == '1':
            tmpl = p
            break
    tbl_id = 1700000000
    inserted = []
    for i, ex in enumerate(exams):
        end = starts[i + 1] if i + 1 < len(starts) else len(top)
        last = None
        for p in top[starts[i]:end]:
            if '⑤' in own_text(p):
                last = p
        box_p = copy.deepcopy(tmpl)
        tbl = box_p.find('.//hp:tbl', NS)
        tbl_id += 1
        tbl.set('id', str(tbl_id))
        tc = tbl.find('.//hp:tc', NS)
        tc.set('borderFillIDRef', h.fill(tc.get('borderFillIDRef'), '#F2F2F2'))
        sub = tc.find(q('subList'))
        ps = sub.findall(q('p'))
        base = ps[0].findall(q('run'))[-1].get('charPrIDRef')   # 굵지 않은 본문 글자
        for extra in ps[1:]:
            sub.remove(extra)
        p1 = ps[0]
        for r in p1.findall(q('run')):
            p1.remove(r)
        p1.append(make_run(h.char(base, RED, bold=True), '정답  %s' % ex['ans']))
        p2 = copy.deepcopy(p1)
        for r in p2.findall(q('run')):
            p2.remove(r)
        p2.append(make_run(h.char(base, BLUE, plain=True), ex['why']))
        p1.addnext(p2)
        inserted.append((last, box_p))
    for last, box_p in inserted:
        last.addnext(box_p)

    # 4) 제목 옆 [교사용]
    for t in root.iter(q('t')):
        if t.text and t.text.strip() == getattr(mod, 'TITLE', '1. 경제 체제 비교'):
            run = t.getparent()
            run.addnext(make_run(h.char(run.get('charPrIDRef'), RED, bold=True), '  [교사용]'))
            break

    files['Contents/section0.xml'] = etree.tostring(root, xml_declaration=True, encoding='UTF-8', standalone=True)
    files['Contents/header.xml'] = h.xml.encode('utf-8')
    with zipfile.ZipFile(out, 'w') as zo:
        for n in z.namelist():
            comp = zipfile.ZIP_STORED if n == 'mimetype' else zipfile.ZIP_DEFLATED
            zo.writestr(zipfile.ZipInfo(n, (1980, 1, 1, 0, 0, 0)), files[n], compress_type=comp)
    print('saved', out, '| 빈칸 %d, OX %d, 판별 %d, 기출 %d' % (len(blank_answers), len(ox), len(sort), len(exams)))


if __name__ == '__main__':
    main(*sys.argv[1:4])
