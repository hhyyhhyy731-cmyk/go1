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

## 단원별 보충 학습지 (「기본권의 유형」 서식)

`template_기본권의유형.hwpx`의 글자·문단·표 서식을 그대로 쓰고 본문만 새로 만듭니다.
내용은 단원별 모듈(`ws_economy1.py` 등)에서 고칩니다.

```bash
cd src
python3 worksheet_hwpx.py template_기본권의유형.hwpx ../통합사회2_Ⅲ-1_자본주의와_경제체제_학습지.hwpx ws_economy1
```
