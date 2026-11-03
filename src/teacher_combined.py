"""한글에서 손본 학생용 학습지(여러 단원을 합친 HWPX)에 정답·풀이를 넣어 교사용을 만든다. 서식은 그대로 둔다.

usage: python3 teacher_combined.py 학생용.hwpx 교사용.hwpx ws_economy1 ws_economy2 ...
  학생용 파일은 단원마다 머리말(“고촌고 1학년 …”)로 시작하고, 모듈 순서와 단원 순서가 같아야 한다.

넣는 것 (정답 빨강, 해설·풀이 파랑)
  · 개념 정리 빈칸 → ( 정답 )  — 문장 내용으로 위치를 찾으므로 순서를 바꿔도 된다
  · 계산표·답칸의 빈 칸 → 정답  — 생성기의 학생용/교사용 표를 비교해서 찾는다
  · OX → 답칸에 O/X, 문장 아래에 해설
  · 풀이 칸이 있는 문항 → 풀이 칸에 풀이 과정과 정답
  · 풀이 칸이 없는 기출 → 마지막 선지 아래에 정답·해설 상자
  · 단원 제목 옆 [교사용]
"""
import copy
import importlib
import re
import sys
import zipfile

from lxml import etree

from sheet_hwpx import Sheet
from teacher_from_student import Header, make_run, split_run, own_text, q, NS, HP, RED, BLUE

BLANK = re.compile(r'\(\s{3,}\)')
WS = re.compile(r'\s+')


def norm(t):
    return WS.sub('', t.replace('·', '').replace('*', ''))


def tmpl_key(t):
    t = re.sub(r'\[\[.+?\]\]', '\x00', t).replace('**', '').replace('__', '')
    return norm(t)


def doc_key(t):
    return norm(BLANK.sub('\x00', t))


def cell_text(tc):
    sub = tc.find(q('subList'))
    return '\n'.join(own_text(p) for p in sub.findall(q('p')))


def cells_of(tbl):
    out = {}
    for tc in tbl.findall('hp:tr/hp:tc', NS):
        a = tc.find(q('cellAddr'))
        out[(int(a.get('rowAddr')), int(a.get('colAddr')))] = tc
    return out


def signature(tbl):
    cs = cells_of(tbl)
    return '|'.join(norm(cell_text(cs[k])) for k in sorted(cs) if norm(cell_text(cs[k])) and not BLANK.fullmatch(cell_text(cs[k]).strip()))


def gen_root(mod, teacher):
    s = Sheet(teacher=teacher)
    mod.build(s)
    xml = s.sec_head + ''.join(s.body) + '</hs:sec>'
    return s, etree.fromstring(xml.encode('utf-8'))


def table_fills(mod):
    """생성기 학생용/교사용을 비교해 ‘학생용에서 빈 칸 → 교사용 답’을 표 서명별로 모은다."""
    _, sr = gen_root(mod, False)
    _, tr = gen_root(mod, True)
    st = list(sr.iter(q('tbl')))
    tt = [t for t in tr.iter(q('tbl')) if not cell_text(list(cells_of(t).values())[0]).startswith('정답')]
    assert len(st) == len(tt), (len(st), len(tt))
    fills = {}
    for a, b in zip(st, tt):
        ca, cb = cells_of(a), cells_of(b)
        f = {}
        for k, tc in ca.items():
            s_t, t_t = cell_text(tc).strip(), cell_text(cb[k]).strip()
            if s_t == t_t:
                continue
            if BLANK.fullmatch(s_t) and re.fullmatch(r'\( .+ \)', t_t):
                continue                      # 문장 빈칸은 blanks() 에서 채운다
            if not s_t or BLANK.fullmatch(s_t):
                f[k] = ('set', t_t)
            elif s_t.endswith('→') and t_t.startswith(s_t):
                f[k] = ('add', t_t[len(s_t):].strip())
        if f:
            fills.setdefault(signature(a), []).append(f)
    return fills


class Builder:
    def __init__(self, path):
        z = zipfile.ZipFile(path)
        self.z = z
        self.files = {n: z.read(n) for n in z.namelist()}
        self.h = Header(self.files['Contents/header.xml'].decode('utf-8'))
        self.root = etree.fromstring(self.files['Contents/section0.xml'])
        for ls in list(self.root.iter(q('linesegarray'))):
            ls.getparent().remove(ls)
        self.log = []

    def red(self, base, bold=True):
        return self.h.char(base, RED, bold=bold)

    def blue(self, base):
        return self.h.char(base, BLUE, plain=True)

    # ── 단원 나누기 ─────────────────────────────────────────
    def regions(self, n):
        top = self.root.findall(q('p'))
        starts = [i for i, p in enumerate(top) if own_text(p).strip().startswith('고촌고 1학년')]
        assert len(starts) == n, '단원 머리말 %d개, 모듈 %d개' % (len(starts), n)
        return [top[s:(starts[k + 1] if k + 1 < n else len(top))] for k, s in enumerate(starts)]

    @staticmethod
    def iter_p(region):
        for tp in region:
            for p in tp.iter(q('p')):
                yield p

    @staticmethod
    def iter_tbl(region):
        for tp in region:
            for t in tp.iter(q('tbl')):
                yield t

    def base_char(self, el):
        r = el.find('.//hp:run', NS)
        return r.get('charPrIDRef') if r is not None else '0'

    # ── 처리 단계 ───────────────────────────────────────────
    def do_unit(self, region, mod):
        name = mod.TITLE
        self.title(region, mod.TITLE)
        self.tables(region, table_fills(mod), name)
        self.ox_notes(region, mod, name)
        self.blanks(region, mod, name)
        self.solutions(region, mod, name)

    def title(self, region, title):
        for p in self.iter_p(region):
            for t in p.iter(q('t')):
                if t.text and t.text.strip() == title:
                    run = t.getparent()
                    run.addnext(make_run(self.red(run.get('charPrIDRef')), '  [교사용]'))
                    return
        self.log.append('%s: 제목을 찾지 못함' % title)

    def tables(self, region, fills, name):
        used = 0
        for tbl in self.iter_tbl(region):
            sig = signature(tbl)
            if sig not in fills or not fills[sig]:
                continue
            f = fills[sig].pop(0)
            cs = cells_of(tbl)
            for k, (mode, ans) in f.items():
                tc = cs.get(k)
                if tc is None:
                    continue
                ps = tc.find(q('subList')).findall(q('p'))
                row_base = self.base_char(tc) if tc.find('.//hp:run', NS) is not None else \
                    self.base_char(cs.get((k[0], 0), tc))
                if mode == 'set':
                    p = ps[0]
                    for r in p.findall(q('run')):
                        p.remove(r)
                    p.append(make_run(self.red(row_base), ans))
                else:
                    ps[-1].append(make_run(self.red(self.base_char(ps[-1])), ' ' + ans))
                used += 1
        left = sum(len(v) for v in fills.values())
        if left:
            self.log.append('%s: 찾지 못한 표 %d개 → %s' % (name, left, [k[:40] for k, v in fills.items() if v]))
        self.log.append('%s: 표 칸 %d개 채움' % (name, used))

    def ox_notes(self, region, mod, name):
        why = {norm(s): w for s, _, w in getattr(mod, 'OX', [])}
        n = 0
        for tbl in self.iter_tbl(region):
            for tc in tbl.findall('hp:tr/hp:tc', NS):
                k = norm(cell_text(tc))
                if k in why:
                    p = tc.find('.//hp:p', NS)
                    np_ = copy.deepcopy(p)
                    for r in np_.findall(q('run')):
                        np_.remove(r)
                    np_.append(make_run(self.h.char(self.base_char(p), BLUE, smaller=50, plain=True), '→ ' + why.pop(k)))
                    p.addnext(np_)
                    n += 1
        self.log.append('%s: OX 해설 %d개 (못 찾음 %d)' % (name, n, len(why)))

    def blanks(self, region, mod, name):
        probe = Sheet()
        probe.blank_src = []
        mod.build(probe)
        groups = []
        for nid, ans, t in probe.blank_src:
            if groups and groups[-1][0] == nid:
                groups[-1][1].append(ans)
            else:
                groups.append([nid, [ans], tmpl_key(t), False])
        filled = fallback = 0
        for p in self.iter_p(region):
            txt = own_text(p)
            k = len(BLANK.findall(txt))
            if not k:
                continue
            key = doc_key(txt)
            g = next((g for g in groups if not g[3] and g[2] == key), None)
            if g is None:
                g = next((g for g in groups if not g[3] and len(g[1]) == k), None)
                if g is None:
                    self.log.append('%s: 정답이 없는 빈칸 → %s' % (name, txt[:40]))
                    continue
                fallback += 1
                self.log.append('%s: 문장이 달라 순서로 맞춤 → %s  =  %s' % (name, txt[:30], g[1]))
            g[3] = True
            answers = iter(g[1])
            for t in [t for t in p.iter(q('t')) if t.text and BLANK.search(t.text) and t.getparent().getparent() is p]:
                pieces, pos = [], 0
                red = self.red(t.getparent().get('charPrIDRef'))
                for m in BLANK.finditer(t.text):
                    a = next(answers, '')
                    pieces += [(None, t.text[pos:m.start()]), (None, '( '), (red, a), (None, ' )')]
                    pos = m.end()
                pieces.append((None, t.text[pos:]))
                split_run(t, pieces)
            filled += 1
        miss = [g[1] for g in groups if not g[3]]
        self.log.append('%s: 빈칸 문장 %d개 채움 (순서로 맞춤 %d, 남은 정답 %d %s)' % (name, filled, fallback, len(miss), miss[:5]))

    def solutions(self, region, mod, name):
        items = []
        for p in getattr(mod, 'PRACTICE', []):
            items.append((norm(p['title']), p['sol'], p['ans']))
        exams = getattr(mod, 'EXAMS', [])
        for e in exams:
            why = e['why'] if isinstance(e['why'], list) else [e['why']]
            items.append((norm(re.sub(r'\*\*|__', '', e['stem']))[:18], why, e['ans']))
        done = set()
        # 1) 풀이 칸이 있는 문항
        for tbl in self.iter_tbl(region):
            if tbl.get('rowCnt') != '1' or tbl.get('colCnt') != '2':
                continue
            cs = cells_of(tbl)
            left, right = cs.get((0, 0)), cs.get((0, 1))
            if left is None or right is None:
                continue
            sub = right.find(q('subList'))
            first = sub.find(q('p'))
            if first is None or own_text(first).strip() != '풀이':
                continue
            lt = norm(cell_text(left)) + norm(''.join(left.xpath('.//hp:t/text()', namespaces=NS)))
            hit = next((i for i, it in enumerate(items) if i not in done and it[0] and it[0] in lt), None)
            if hit is None:
                self.log.append('%s: 풀이 칸의 문항을 못 찾음 → %s' % (name, cell_text(left)[:30]))
                continue
            done.add(hit)
            _, sol, ans = items[hit]
            base = self.base_char(first)
            for line in sol:
                np_ = copy.deepcopy(first)
                for r in np_.findall(q('run')):
                    np_.remove(r)
                for k, part in enumerate(re.split(r'\*\*', line)):
                    if part:
                        np_.append(make_run(self.h.char(base, BLUE, bold=bool(k % 2), plain=not k % 2), part))
                sub.append(np_)
            np_ = copy.deepcopy(first)
            for r in np_.findall(q('run')):
                np_.remove(r)
            np_.append(make_run(self.red(base), '정답  %s' % ans))
            sub.append(np_)
        # 2) 풀이 칸이 없는 기출 → 마지막 선지 아래 상자
        off = len(getattr(mod, 'PRACTICE', []))
        top = list(region)
        tmpl = None
        for tp in top:
            for t in tp.iter(q('tbl')):
                if t.get('rowCnt') == '1' and t.get('colCnt') == '1':
                    tmpl = tp
                    break
            if tmpl is not None:
                break
        for i, e in enumerate(exams):
            if off + i in done:
                continue
            key = items[off + i][0]
            start = next((j for j, tp in enumerate(top) if key and key in norm(own_text(tp))), None)
            if start is None:
                self.log.append('%s: 기출 %d번을 못 찾음' % (name, i + 1))
                continue
            last = None
            for tp in top[start:]:
                if tp is not top[start] and re.match(r'\s*\d+\.', own_text(tp)) and tp.find('.//hp:tbl', NS) is None \
                        and own_text(tp).strip()[:2] != own_text(top[start]).strip()[:2]:
                    break
                if '⑤' in own_text(tp):
                    last = tp
                    break
            if last is None or tmpl is None:
                self.log.append('%s: 기출 %d번 선지를 못 찾음' % (name, i + 1))
                continue
            box = copy.deepcopy(tmpl)
            # 상자 앞뒤 다른 글자는 지운다
            for r in box.findall(q('run')):
                for t in r.findall(q('t')):
                    r.remove(t)
            tbl = box.find('.//hp:tbl', NS)
            tbl.set('id', str(1800000000 + i + 100 * off))
            tc = tbl.find('.//hp:tc', NS)
            tc.set('borderFillIDRef', self.h.fill(tc.get('borderFillIDRef'), '#F2F2F2'))
            sub = tc.find(q('subList'))
            ps = sub.findall(q('p'))
            base = self.base_char(ps[0])
            for extra in ps[1:]:
                sub.remove(extra)
            p1 = ps[0]
            for r in p1.findall(q('run')):
                p1.remove(r)
            p1.append(make_run(self.red(base), '정답  %s' % e['ans']))
            for line in items[off + i][1]:
                p2 = copy.deepcopy(p1)
                for r in p2.findall(q('run')):
                    p2.remove(r)
                p2.append(make_run(self.blue(base), line.replace('**', '')))
                sub.append(p2)
            last.addnext(box)
            done.add(off + i)
        self.log.append('%s: 풀이·정답 %d / %d 문항' % (name, len(done), len(items)))

    def save(self, out):
        self.files['Contents/section0.xml'] = etree.tostring(self.root, xml_declaration=True, encoding='UTF-8',
                                                             standalone=True)
        self.files['Contents/header.xml'] = self.h.xml.encode('utf-8')
        with zipfile.ZipFile(out, 'w') as zo:
            for n in self.z.namelist():
                comp = zipfile.ZIP_STORED if n == 'mimetype' else zipfile.ZIP_DEFLATED
                zo.writestr(zipfile.ZipInfo(n, (1980, 1, 1, 0, 0, 0)), self.files[n], compress_type=comp)


def main(src, out, *mods):
    b = Builder(src)
    modules = [importlib.import_module(m) for m in mods]
    for region, mod in zip(b.regions(len(modules)), modules):
        b.do_unit(region, mod)
    b.save(out)
    print('\n'.join(b.log))
    print('saved', out)


if __name__ == '__main__':
    main(*sys.argv[1:])
