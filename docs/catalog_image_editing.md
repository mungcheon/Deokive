# Catalog Image Editing

상품 사진이 잘못 들어갔거나 비어 있을 때 직접 고치는 방법입니다.
수정 기준은 `data/catalog_public.json` 안의 `catalog_index`입니다.

## 1. 상품 찾기

먼저 상품의 `catalog_index`를 찾습니다.

```powershell
python -X utf8 tools\find_catalog_rows.py "치이카와" "러버 스트랩" --missing-image
```

전체 DB에서 찾고 싶으면 `--missing-image`를 빼면 됩니다.

```powershell
python -X utf8 tools\find_catalog_rows.py "단간론파" "모노쿠마"
```

## 2. 이미지 출처 확인

가능하면 공식 상품 상세 페이지, 제조사 페이지, 공식 판매 페이지 이미지를 사용합니다.

확인 기준:

- 상품명, 캐릭터, 버전이 같아야 합니다.
- 같은 시리즈라도 다른 캐릭터 사진은 넣지 않습니다.
- 검색 결과 썸네일만 보고 넣지 않습니다.
- 라스트원상, 더블찬스, 재발매 상품은 캠페인명이 다르면 별도 상품으로 남깁니다.

## 3. 이미지 저장하기

먼저 dry-run으로 확인합니다.

```powershell
python -X utf8 tools\apply_manual_catalog_image_update.py 920 "이미지URL" --source-url "상품상세URL" --expect-name "러버 스트랩"
```

문제가 없으면 `--write`를 붙입니다.

```powershell
python -X utf8 tools\apply_manual_catalog_image_update.py 920 "이미지URL" --source-url "상품상세URL" --expect-name "러버 스트랩" --write
```

이 명령은 아래를 같이 처리합니다.

- `data/catalog_public.json`의 `image_url`, `source_url`, `local_image_path` 갱신
- 앱용 이미지 저장: `assets/catalog_images/`
- GitHub Pages용 이미지 저장: `assets/assets/catalog_images/`

상품명도 같이 고쳐야 할 때:

```powershell
python -X utf8 tools\apply_manual_catalog_image_update.py 920 "이미지URL" --source-url "상품상세URL" --expect-name "러버 스트랩" --name-ko "새 한국어 이름" --name-ja "새 일본어 이름" --write
```

## 4. 리포트 갱신 및 검사

```powershell
python -X utf8 tools\update_public_catalog_reports.py --write
python -X utf8 tools\audit_public_catalog_image_assets.py
python -X utf8 tools\audit_public_catalog_safety.py
```

검사가 통과하면 커밋해도 됩니다.
