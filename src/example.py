"""2차시 작성지 예시 답안 — 앞면 국회 전자청원문, 뒷면 결정문.
usage: python3 example.py blocks.json  /  python3 build_hwpx.py out.hwpx example

본문은 문단 단위로 적고 wrap()이 작성지 한 줄 폭에 맞춰 나눈다.
__밑줄__ 표시는 밑줄(헌법 조문·근거 자료)로 출력된다.
"""
import json
import re
import content as C
from content import title, p, name, grid, c, BLUE

C.blocks.clear()
blocks = C.blocks

INK = '1F2D5A'          # 손글씨 느낌의 남색
LINE_UNITS = 45         # 9.5pt 기준 한 줄에 들어가는 한글 글자 수(여유 포함)


def _w(ch):
    if ch == ' ':
        return 0.33
    return 0.55 if ord(ch) < 128 else 1.0


def wrap(paragraphs):
    """[(기준 번호, 문단)] → 작성지 줄 목록. 어절 단위로 끊고 문단 첫 줄에만 기준 번호를 단다."""
    rows = []
    for crit, text in paragraphs:
        chars = []                       # (글자, 밑줄 여부)
        for k, part in enumerate(re.split(r'__', text)):
            chars += [(ch, k % 2 == 1) for ch in part]
        words, cur = [], []
        for ch in chars:
            cur.append(ch)
            if ch[0] == ' ':
                words.append(cur); cur = []
        if cur:
            words.append(cur)
        line, width, first = [], 0.0, True
        def flush():
            nonlocal line, width, first
            segs = []
            for ch, u in line:
                if segs and segs[-1][1] == u:
                    segs[-1][0] += ch
                else:
                    segs.append([ch, u])
            rows.append(dict(segs=segs, crit=crit if first else ''))
            line, width, first = [], 0.0, False
        for word in words:
            ww = sum(_w(ch) for ch, _ in word)
            if line and width + ww > LINE_UNITS:
                flush()
            line += word; width += ww
        if line:
            flush()
    return rows


def answer_sheet(head, paragraphs, n):
    rows = wrap(paragraphs)
    assert len(rows) <= n, f'{head}: {len(rows)}줄 > {n}줄'
    blocks.append(dict(k='lined', head=head, n=n, h=9.5, crit_w=13, rows=rows, color=INK))


def filled_form(rows):
    grid([40, 140], [[c(label, fill=BLUE, bold=True, align='center'),
                      c([dict(t=t, size=9.5, color=INK) for t in text])] for label, text in rows])


NOTE = '※ 교사용 예시 답안입니다. 근거 자료의 ○○ 부분은 학생이 조사지에 적은 실제 기사·통계로 바뀝니다.'

# ───────── 앞면: 국회 전자청원문 ─────────
title('[예시 답안] 국회 전자청원문 (앞면)', '헌법 제26조 ① 모든 국민은 법률이 정하는 바에 의하여 국가기관에 문서로 청원할 권리를 가진다.')
p(NOTE, size=8, color='C00000')
name()
p(' ', size=4)
filled_form([
    ('청원 제목', ['5명 미만 사업장 노동자에게도 근로기준법을 똑같이 적용해 주십시오']),
    ('청원의 취지', ['근로기준법 제11조를 개정하여 상시 5명 미만 사업장 노동자에게도 가산수당, '
                   '연차휴가, 부당해고 구제 규정을 적용해 줄 것을 청원합니다.']),
])
p(' ', size=4)
answer_sheet('【청원 내용】', [
    ('①', '저는 고등학생이고 주말마다 동네 식당에서 아르바이트를 합니다. 이 식당은 직원이 4명이라 밤늦게까지 '
          '일해도 야간 수당을 받지 못하고, 갑자기 그만두라는 말을 들어도 부당해고 구제를 신청할 수 없다고 합니다.'),
    ('③', '그 원인은 근로기준법 제11조입니다. 이 조항은 법 전체를 상시 5명 이상 사업장에 적용하고, 5명 미만 '
          '사업장에는 대통령령으로 정한 일부 규정만 적용하도록 하고 있습니다.'),
    ('②④', '이는 __헌법 제11조 제1항__의 평등권과 __헌법 제32조 제1항__의 근로의 권리를 침해한다고 생각합니다. '
           '__헌법 제32조 제3항__도 근로조건의 기준은 인간의 존엄성을 보장하도록 법률로 정한다고 하였습니다.'),
    ('⑤', '같은 시간 같은 일을 하는데 사업장 크기만으로 보호가 달라지는 것은 합리적인 차별이라고 보기 어렵습니다. '
          '__○○일보(20○○. ○. ○.) 기사__에서도 5명 미만 사업장 노동자가 수당 없이 밤늦게까지 일한 사례가 소개되었습니다. '
          '이런 곳에는 경험이 적은 청소년이 많이 일해 피해가 더 큽니다. 작은 가게의 부담이 커진다는 반대 의견도 있으므로, '
          '가산수당부터 단계적으로 적용하고 영세 사업주에게 인건비를 지원하는 방법을 함께 제안합니다.'),
    ('⑥', '국회는 근로기준법 제11조를 개정하여 모든 노동자가 똑같이 보호받게 해 주십시오.'),
    ('⑦', '저도 학교에서 청소년 노동인권 캠페인을 열고, 친구들과 함께 이 청원에 동의를 모으겠습니다.'),
], 16)
p('20    년    월    일            청원인:   ○ ○ ○                (서명)', align='right', before=2)
p('대한민국 국회 귀중', bold=True, size=12, align='center')
C.brk()

# ───────── 뒷면: 헌법재판소 결정문 ─────────
title('[예시 답안] 헌법재판소 결정문 (뒷면)', '나는 헌법재판관입니다. 청구인과 국가의 입장을 모두 듣고 판단합니다.')
p('※ 예시 사례: 제대군인 가산점 사건(헌재 1999. 12. 23. 98헌마363). 학생은 조사지 뒷면에 적은 자기 사례로 씁니다.', size=8, color='C00000')
p(' ', size=4)
answer_sheet('결정문 본문', [
    ('⑥', '【사건】 제대군인지원에관한법률 제8조 제1항 등 위헌확인'),
    ('', '【청구인】 공무원 채용시험을 준비하던 여성들과 장애가 있는 남성'),
    ('④', '【주문】 제대군인 가산점 제도를 정한 이 법률조항은 헌법에 위반된다.'),
    ('', '【이유】'),
    ('①', '1. 사건 개요: 이 법은 군대를 다녀온 사람이 공무원 시험에 응시하면 과목별 만점의 3~5%를 더해 주었다. '
          '대부분의 여성과 장애인은 군 복무를 하지 않아 가산점을 받을 수 없었고, 적은 점수 차로 합격이 갈리는 시험에서 '
          '크게 불리해졌다. 그래서 청구인들은 평등권과 공무담임권이 침해되었다며 헌법소원을 청구하였다.'),
    ('②', '2. 쟁점: 제대군인의 사회 복귀를 돕는 공익과 여성·장애인의 평등권 및 공무담임권이 충돌한다.'),
    ('③', '3. 관련 조문: __헌법 제11조 제1항__(평등권), __제25조__(공무담임권), __제32조 제4항__(여성 근로 차별 금지), '
          '__제37조 제2항__(기본권 제한의 한계)'),
    ('⑤', '4. 판단: 병역 의무를 마친 사람의 사회 복귀를 돕는다는 목적은 정당하다. 그러나 가산점은 시험을 보는 일부 '
          '제대군인만 돕고 그 부담을 여성과 장애인에게 지우는 방법이다. 취업 알선이나 직업 훈련처럼 다른 사람의 기회를 '
          '빼앗지 않는 지원 방법도 있다. 소수점 차이로 당락이 갈리는 시험에서 가산점은 여성과 장애인의 공직 진출을 '
          '사실상 막으므로, 얻는 공익보다 침해되는 기본권이 훨씬 크다.'),
    ('④', '5. 결론: 그러므로 이 법률조항은 평등권과 공무담임권을 침해하여 헌법에 위반된다. (실제 결정과 같음)'),
], 21)
p('20    년    월    일            재판관:   ○ ○ ○                (서명)', align='right', before=2)

if __name__ == '__main__':
    import sys
    json.dump(blocks, open(sys.argv[1], 'w'), ensure_ascii=False)
