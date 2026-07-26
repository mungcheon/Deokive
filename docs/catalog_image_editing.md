# Catalog Image Editing

잘못 들어간 상품 사진이나 빈 사진은 `catalog_index` 기준으로 고칩니다.

## 1. 상품 번호 찾기

사이트 DB 보기에서 상품을 검색한 뒤, 개발용 데이터에서는 `data/catalog_public.json`의 `catalog_index` 값을 확인합니다.

```powershell
python -X utf8 - <<'PY'
import json
from pathlib import Path
rows=json.loads(Path('data/catalog_public.json').read_text(encoding='utf-8'))['items']
for row in rows:
    if '검색어' in (row.get('name_ko') or ''):
        print(row['catalog_index'], row.get('name_ko'), row.get('name_ja'))
PY
```

## 2. 공식 출처 확인

이미지는 가능하면 공식 상품 상세 페이지, 제조사 페이지, 공식 판매 페이지에서 가져옵니다.

확인 기준:

- 상품명과 캐릭터/버전이 정확히 같아야 합니다.
- 검색 결과 페이지나 카테고리 페이지는 출처로 쓰지 않습니다.
- 비슷한 상품, 재발매, 같은 상의 다른 캐릭터 이미지는 넣지 않습니다.

## 3. 이미지와 출처 넣기

먼저 dry-run으로 확인합니다.

```powershell
python -X utf8 tools\apply_manual_catalog_image_update.py 1455 "이미지URL" --source-url "상품상세URL"
```

문제가 없으면 `--write`를 붙입니다.

```powershell
python -X utf8 tools\apply_manual_catalog_image_update.py 1455 "이미지URL" --source-url "상품상세URL" --write
```

이 명령은 아래를 같이 처리합니다.

- `data/catalog_public.json`의 `image_url`, `source_url`, `local_image_path` 갱신
- 앱용 이미지 저장: `assets/catalog_images/`
- GitHub Pages용 이미지 저장: `assets/assets/catalog_images/`

상품명이 틀린 경우에는 같이 바꿀 수 있습니다.

```powershell
python -X utf8 tools\apply_manual_catalog_image_update.py 1455 "이미지URL" --source-url "상품상세URL" --name-ko "새 한국어명" --name-ja "새 일본어명" --write
```

## 4. 확인

```powershell
python -X utf8 tools\audit_public_catalog_image_assets.py
python -X utf8 tools\audit_public_catalog_safety.py
```

두 검사 모두 통과하면 커밋해도 됩니다.
