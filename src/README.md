# 양식 생성 스크립트

내용은 `content.py` 한 곳에서 고치면 Word·한글 파일에 같이 반영됩니다.

```bash
python3 src/content.py blocks.json
node src/build.js blocks.json 통합사회_수행평가_국민청원문_결정문.docx      # npm install docx
python3 src/build_hwpx.py 통합사회_수행평가_국민청원문_결정문.hwpx        # pip install python-hwpx (src 폴더에서 실행)
```
