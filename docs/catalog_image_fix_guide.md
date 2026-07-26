# Catalog Image Fix Guide

공개 DB에서 사진이 없거나 잘못 들어간 항목은 정확한 공식 상세 페이지와 그 상세 페이지 안의 상품 이미지를 확인한 뒤에만 수정합니다.

## 직접 수정하는 빠른 방법

1. `data/catalog_public.json`에서 `catalog_index` 또는 `name_ko`로 항목을 찾습니다.
2. 사진이 틀렸고 정확한 대체 사진을 아직 못 찾았다면 아래 3개 필드를 비워 둡니다.
   - `source_url`
   - `image_url`
   - `local_image_path`
3. 정확한 공식 상품 상세 페이지를 찾으면 `source_url`에 넣습니다.
4. 같은 상세 페이지 안의 상품 이미지 URL을 `image_url`에 넣습니다.
5. 로컬 저장 이미지는 직접 파일명을 만들지 말고 캐시 명령으로 다시 받습니다.

```powershell
python -X utf8 tools\cache_catalog_images.py --write
python -X utf8 tools\update_public_catalog_reports.py --write
python -X utf8 tools\audit_public_catalog_safety.py
python -X utf8 tools\audit_public_catalog_image_assets.py
```

## 확인 큐로 고치는 방법

사진 없는 항목은 `data/catalog_image_attachment_action_queue_public.json`에서 확인합니다.

- `next_representative_image_review_batch`: 공식 페이지는 있지만 대표 이미지가 정확한 굿즈 종류와 맞는지 확인해야 하는 항목입니다.
- `source_url_update_template`: 검색 결과나 상점 메인 URL만 있어서 정확한 상품 상세 페이지부터 찾아야 하는 항목입니다.

정확한 이미지가 확인되면 `server/catalog_image_attachment_confirmed_rows.json`에 아래 형태로 넣고 import합니다.

```json
{
  "manual_confirmed": true,
  "row_index": 936,
  "field": "image_url",
  "manual_value": "https://example.com/product-image.jpg",
  "evidence_url": "https://example.com/product-page",
  "candidate_source_url": "https://example.com/product-page",
  "name_ko": "상품명"
}
```

```powershell
python -X utf8 tools\import_confirmed_image_attachment_rows.py
python -X utf8 tools\import_confirmed_image_attachment_rows.py --write
python -X utf8 tools\cache_catalog_images.py --write
python -X utf8 tools\update_public_catalog_reports.py --write
```

## 주의

- 검색 결과, 상점 메인, 카테고리 페이지, OGP 이미지, 로고, 배너 이미지는 사용하지 않습니다.
- 같은 캐릭터여도 굿즈 종류가 다르면 넣지 않습니다. 예: 마스코트 항목에 아크릴스탠드 사진 금지.
- 이치방쿠지는 `발매명 + 상 이름 + 종류`가 모두 맞는지 확인합니다.
- 라스트원상과 더블찬스처럼 공식 정가가 없거나 경품 성격인 항목은 가격을 `0`으로 둡니다.
