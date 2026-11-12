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

1학년 사회 불평등 수행평가(내용: `inequality.py`, 안내문: `inequality_notice.py`):

```bash
python3 src/inequality.py blocks.json && node src/build.js blocks.json 1학년_통합사회_사회불평등_수행평가지.docx
python3 src/inequality_notice.py blocks.json && node src/build.js blocks.json 1학년_통합사회_사회불평등_안내문.docx
python3 src/build_hwpx.py 1학년_통합사회_사회불평등_수행평가지.hwpx inequality        # src 폴더에서 실행
python3 src/build_hwpx.py 1학년_통합사회_사회불평등_안내문.hwpx inequality_notice     # src 폴더에서 실행
```
