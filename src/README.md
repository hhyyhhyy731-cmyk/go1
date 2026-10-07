# 양식 생성 스크립트

내용은 `content.py` 한 곳에서 고치면 Word·한글 파일에 같이 반영됩니다.

```bash
python3 src/content.py blocks.json
node src/build.js blocks.json 통합사회_수행평가_전자청원문_결정문.docx      # npm install docx
python3 src/build_hwpx.py 통합사회_수행평가_전자청원문_결정문.hwpx        # pip install python-hwpx (src 폴더에서 실행)
```

예시 답안(내용: `example.py`):

```bash
python3 src/build_hwpx.py 통합사회_수행평가_예시답안.hwpx example   # src 폴더에서 실행
```

## 단원별 보충 학습지

글꼴은 모두 한컴산뜻돋움, 표의 항목 칸은 가운데 정렬, 기출문제는 2단입니다.
내용은 단원별 모듈(`ws_economy1.py` 등)에서 고치고, 빈칸은 `[[정답]]`(긴 빈칸)·`[[정답|s]]`(짧은 빈칸)로 씁니다.

```bash
cd src
# 처음 만들 때: 학생용·교사용 생성 (교사용은 정답 빨강, 해설 파랑)
python3 sheet_hwpx.py ../학생용.hwpx ws_economy1
python3 sheet_hwpx.py ../교사용.hwpx ws_economy1 --teacher

# 학생용을 한글에서 손본 뒤: 그 파일 서식 그대로 정답만 넣어 교사용 만들기
python3 teacher_from_student.py ../통합사회2_Ⅲ-1_경제체제_비교_학습지.hwpx ws_economy1 ../통합사회2_Ⅲ-1_경제체제_비교_학습지_교사용.hwpx
```

`teacher_from_student.py`는 학생용의 빈칸 `(   )`을 순서대로 찾아 개념 정리 정답과 OX 답을 넣고,
판별 답칸·OX 해설·기출 정답 상자를 문항 자리에 추가합니다. 빈칸 수가 정답 수와 다르면 멈추고 알려 줍니다.
