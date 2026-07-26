# Catalog Image Editing

사진이 없거나 잘못 들어간 상품을 직접 고치는 방법입니다.

수정 기준 ID는 `data/catalog_public.json` 안의 `catalog_index`입니다. 사이트와 앱에 실제로 뜨게 하려면 URL만 넣지 말고, 반드시 아래 도구로 로컬 이미지 캐시까지 같이 만들어야 합니다.

## 1. 상품 찾기

사진 없는 항목만 찾기:

```powershell
python -X utf8 tools\find_catalog_rows.py "치이카와" "러버 스트랩" --missing-image
```

사진이 이미 들어간 상품까지 전체 DB에서 찾기:

```powershell
python -X utf8 tools\find_catalog_rows.py "단간론파" "모노쿠마"
```

출력에서 고칠 상품의 `catalog_index`를 확인합니다.

## 2. 이미지 확인 기준

가능하면 공식 상품 상세 페이지, 제조사 페이지, 공식 판매 페이지, 공식 보도자료 이미지를 사용합니다.

체크할 것:

- 상품명, 캐릭터, 버전, 상 이름이 같은지 확인합니다.
- 같은 시리즈라도 다른 캐릭터 사진을 넣지 않습니다.
- 검색 결과 썸네일만 보고 넣지 말고, 상세 페이지에서 이미지와 상품명을 확인합니다.
- 재발매, 더블찬스, 라스트원상, 한정 매장/카페명, 버전명이 다르면 별도 상품으로 봅니다.

## 3. 이미지 저장하기

먼저 dry-run으로 확인합니다.

```powershell
python -X utf8 tools\apply_manual_catalog_image_update.py 920 "이미지URL" --source-url "상품상세URL" --expect-name "현재상품명"
```

문제가 없으면 `--write`를 붙여 실제 반영합니다.

```powershell
python -X utf8 tools\apply_manual_catalog_image_update.py 920 "이미지URL" --source-url "상품상세URL" --expect-name "현재상품명" --write
```

이 명령은 아래를 한 번에 처리합니다.

- `data/catalog_public.json`의 `image_url`, `source_url`, `local_image_path` 갱신
- 실제 이미지 파일을 `assets/catalog_images/`에 저장
- GitHub Pages용 이미지 파일을 `assets/assets/catalog_images/`에 저장
- Flutter 내장 DB `lib/data/catalog/seed_catalog.dart` 갱신

상품명도 같이 고칠 때:

```powershell
python -X utf8 tools\apply_manual_catalog_image_update.py 920 "이미지URL" --source-url "상품상세URL" --expect-name "현재상품명" --name-ko "한국어 상품명" --name-ja "일본어 상품명" --write
```

## 4. 검증하기

수정 후 아래 검사를 실행합니다.

```powershell
python -X utf8 tools\update_public_catalog_reports.py --write
python -X utf8 tools\audit_flutter_seed_matches_public.py
python -X utf8 tools\audit_public_catalog_image_assets.py
python -X utf8 tools\audit_public_catalog_safety.py
```

검사가 통과하면 커밋하고 푸시하면 됩니다.
