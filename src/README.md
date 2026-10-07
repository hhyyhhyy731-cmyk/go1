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

## 단원별 보충 학습지 (흑백 인쇄용)

한글 기본 빈 문서(`template_blank.hwpx`)에 글자·문단·표 서식을 새로 정의해 만듭니다.
본문·문제는 함초롬바탕, 제목·표 항목은 함초롬돋움을 쓰고, 기출문제와 정답은 2단으로 배치합니다.
내용은 단원별 모듈(`ws_economy1.py` 등)에서 고칩니다.

```bash
cd src
python3 sheet_hwpx.py ../통합사회2_Ⅲ-1_경제체제_비교_학습지.hwpx ws_economy1
python3 sheet_hwpx.py ../통합사회2_Ⅲ-1_경제체제_비교_학습지_교사용.hwpx ws_economy1 --teacher
```

빈칸은 내용 안에 `[[정답]]`(긴 빈칸)·`[[정답|s]]`(짧은 빈칸)로 씁니다. 학생용은 빈칸으로, 교사용은 정답을 채워 출력하고
OX·판별 답과 해설, 기출 정답·해설을 문항 바로 아래에 넣습니다(교사용에는 별도 정답 쪽이 없습니다).
