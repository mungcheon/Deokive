# Catalog Image Editing

상품 사진이 비어 있거나 잘못 들어간 경우 직접 고치는 방법입니다.
수정 기준 ID는 `data/catalog_public.json` 안의 `catalog_index`입니다.

## 1. 상품 찾기

먼저 수정할 상품을 찾습니다.

```powershell
python -X utf8 tools\find_catalog_rows.py "치이카와" "러버 스트랩" --missing-image
```

이미지가 이미 들어간 상품까지 전체 DB에서 찾고 싶으면 `--missing-image`를 빼면 됩니다.

```powershell
python -X utf8 tools\find_catalog_rows.py "단간론파" "모노쿠마"
```

## 2. 이미지 출처 확인

가능하면 공식 상품 상세 페이지, 제조사 페이지, 공식 판매 페이지 이미지를 사용합니다.

확인 기준:

- 상품명, 캐릭터, 버전, 상 이름이 같은지 확인합니다.
- 같은 시리즈라도 다른 캐릭터 사진은 넣지 않습니다.
- 검색 결과 썸네일만 보고 넣지 말고, 상세 페이지에서 이미지와 상품명을 확인합니다.
- 재발매, 더블찬스, 라스트원상은 캠페인명이나 상 이름이 다르면 별도 상품으로 봅니다.

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
- 실제 이미지 파일을 `assets/catalog_images/`에 저장
- GitHub Pages용 이미지 파일을 `assets/assets/catalog_images/`에 저장
- Flutter 앱 내장 DB인 `lib/data/catalog/seed_catalog.dart` 갱신

상품명도 같이 고쳐야 한다면 이렇게 넣습니다.

```powershell
python -X utf8 tools\apply_manual_catalog_image_update.py 920 "이미지URL" --source-url "상품상세URL" --expect-name "러버 스트랩" --name-ko "한국어 상품명" --name-ja "일본어 상품명" --write
```

## 4. 확인하기

수정 후 아래 검사를 돌립니다.

```powershell
python -X utf8 tools\update_public_catalog_reports.py --write
python -X utf8 tools\audit_flutter_seed_matches_public.py
python -X utf8 tools\audit_public_catalog_image_assets.py
python -X utf8 tools\audit_public_catalog_safety.py
```

검사가 통과하면 커밋할 수 있습니다.
