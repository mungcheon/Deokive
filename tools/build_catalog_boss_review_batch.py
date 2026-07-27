from __future__ import annotations

import argparse
import html
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CATALOG = ROOT / "data" / "catalog_public.json"
DEFAULT_LEDGER = ROOT / "server" / "boss_review" / "boss_review_ledger.json"
DEFAULT_BATCH_JSON = ROOT / "server" / "boss_review" / "boss_review_current.json"
DEFAULT_BATCH_HTML = ROOT / "server" / "boss_review" / "catalog_boss_review.html"

ALLOWED_STATUSES = {
    "image_error": "사진오류",
    "content_error": "내용오류",
    "fixed_pass": "수정후통과",
    "pass": "통과",
}
APPROVED_STATUSES = {"fixed_pass", "pass"}


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _catalog_items(path: Path) -> list[dict[str, Any]]:
    payload = _read_json(path, {})
    if isinstance(payload, dict):
        items = payload.get("items") or []
    else:
        items = payload
    if not isinstance(items, list):
        raise ValueError(f"{path} must contain a list or an object with an items list")
    return [item for item in items if isinstance(item, dict)]


def _row_index(index: int, item: dict[str, Any]) -> int:
    value = item.get("catalog_index")
    if isinstance(value, bool):
        return index
    if isinstance(value, int):
        return value
    return index


def _reviewed_indexes(ledger_path: Path) -> set[int]:
    ledger = _read_json(ledger_path, {"decisions": []})
    decisions = ledger.get("decisions") if isinstance(ledger, dict) else []
    reviewed: set[int] = set()
    for decision in decisions or []:
        if not isinstance(decision, dict):
            continue
        row_index = decision.get("row_index")
        if isinstance(row_index, bool) or not isinstance(row_index, int):
            continue
        reviewed.add(row_index)
    return reviewed


def _display_name(item: dict[str, Any]) -> str:
    return str(
        item.get("name_ko")
        or item.get("name_ja")
        or item.get("name_en")
        or item.get("name")
        or "이름 없음"
    )


def _issues(item: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if not item.get("image_url") and not item.get("local_image_path"):
        issues.append("사진 없음")
    if not item.get("source_url"):
        issues.append("출처 없음")
    if not item.get("character_name"):
        issues.append("캐릭터명 없음")
    if not item.get("release_date"):
        issues.append("발매일 없음")
    if item.get("official_price_jpy") in (None, "") and item.get("official_price_krw") in (None, ""):
        issues.append("정가 없음")
    return issues


def _review_item(index: int, item: dict[str, Any]) -> dict[str, Any]:
    row_index = _row_index(index, item)
    return {
        "row_index": row_index,
        "catalog_index": item.get("catalog_index", row_index),
        "display_name": _display_name(item),
        "name_ko": item.get("name_ko"),
        "name_ja": item.get("name_ja"),
        "name_en": item.get("name_en"),
        "affiliation": item.get("affiliation"),
        "series_name": item.get("series_name"),
        "sub_series": item.get("sub_series"),
        "category": item.get("category"),
        "character_name": item.get("character_name"),
        "official_price_jpy": item.get("official_price_jpy"),
        "official_price_krw": item.get("official_price_krw"),
        "barcode": item.get("barcode"),
        "release_date": item.get("release_date"),
        "source_store": item.get("source_store"),
        "source_url": item.get("source_url"),
        "image_url": item.get("image_url"),
        "local_image_path": item.get("local_image_path"),
        "issues": _issues(item),
    }


def build_batch(
    *,
    catalog_path: Path = DEFAULT_CATALOG,
    ledger_path: Path = DEFAULT_LEDGER,
    batch_size: int = 10,
    start: int | None = None,
) -> dict[str, Any]:
    items = _catalog_items(catalog_path)
    reviewed = _reviewed_indexes(ledger_path)
    indexed = [(index, item) for index, item in enumerate(items)]

    if start is not None:
        candidates = [(index, item) for index, item in indexed if _row_index(index, item) >= start]
    else:
        candidates = [(index, item) for index, item in indexed if _row_index(index, item) not in reviewed]

    selected = candidates[:batch_size]
    batch_number = (selected[0][0] // batch_size) + 1 if selected else 0
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    review_items = [_review_item(index, item) for index, item in selected]
    all_review_items = [_review_item(index, item) for index, item in indexed]

    return {
        "meta": {
            "generated_at": generated_at,
            "catalog_path": str(catalog_path.relative_to(ROOT) if catalog_path.is_relative_to(ROOT) else catalog_path),
            "ledger_path": str(ledger_path.relative_to(ROOT) if ledger_path.is_relative_to(ROOT) else ledger_path),
            "batch_size": batch_size,
            "batch_number": batch_number,
            "total_items": len(items),
            "reviewed_items": len(reviewed),
            "pending_items": max(len(items) - len(reviewed), 0),
            "selected_items": len(review_items),
            "first_row_index": review_items[0]["row_index"] if review_items else None,
            "last_row_index": review_items[-1]["row_index"] if review_items else None,
            "allowed_statuses": ALLOWED_STATUSES,
            "approved_statuses": sorted(APPROVED_STATUSES),
        },
        "items": review_items,
        "review_items": all_review_items,
    }


def _json_script(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")


def render_html(payload: dict[str, Any]) -> str:
    meta = payload["meta"]
    total = int(meta["total_items"])
    reviewed = int(meta["reviewed_items"])
    selected = int(meta["selected_items"])
    pct = round((reviewed / total) * 100, 2) if total else 0
    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Deokive Boss Review</title>
  <style>
    :root {{
      --ink:#1d1d1f; --sub:#6d737d; --line:#e6e8ee; --paper:#fff; --back:#f5f6f8;
      --brand:#5867e8; --ok:#43aa6d; --warn:#f0a22e; --bad:#e45858; --soft:#eef2f7;
      font-family:-apple-system,BlinkMacSystemFont,"SF Pro Display","Segoe UI",sans-serif;
      color-scheme:light;
    }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; min-height:100vh; background:var(--back); color:var(--ink); }}
    button, textarea {{ font:inherit; }}
    .shell {{ width:min(1280px,100%); margin:0 auto; padding:18px; display:grid; grid-template-columns:minmax(0,1fr) 340px; gap:16px; }}
    header, aside, .card {{ background:rgba(255,255,255,.95); border:1px solid var(--line); box-shadow:0 18px 42px rgba(24,28,38,.08); }}
    header {{ grid-column:1/-1; border-radius:28px; padding:16px 18px; display:flex; justify-content:space-between; gap:14px; align-items:center; }}
    h1,h2,h3,p {{ margin:0; letter-spacing:0; }}
    h1 {{ font-size:23px; }}
    .muted {{ color:var(--sub); font-size:13px; line-height:1.35; margin-top:4px; }}
    .summary {{ display:flex; gap:8px; flex-wrap:wrap; justify-content:flex-end; }}
    .pill {{ padding:8px 10px; border-radius:999px; background:var(--soft); font-size:12px; font-weight:900; white-space:nowrap; }}
    .grid {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:12px; }}
    .card {{ border-radius:24px; padding:14px; display:grid; grid-template-columns:112px minmax(0,1fr); gap:13px; min-height:210px; }}
    .thumb {{ width:112px; height:112px; border-radius:18px; background:var(--soft); border:1px solid var(--line); object-fit:cover; }}
    .empty-thumb {{ width:112px; height:112px; border-radius:18px; background:var(--soft); display:grid; place-items:center; color:var(--sub); font-size:12px; font-weight:900; text-align:center; padding:10px; }}
    .title {{ font-size:15px; line-height:1.25; font-weight:900; word-break:keep-all; overflow-wrap:anywhere; }}
    .meta {{ margin-top:8px; display:grid; gap:4px; color:var(--sub); font-size:12px; line-height:1.3; }}
    .issue-row {{ display:flex; flex-wrap:wrap; gap:5px; margin-top:8px; }}
    .issue {{ padding:5px 7px; border-radius:999px; background:#fff3db; color:#92600f; font-size:11px; font-weight:900; }}
    .actions {{ grid-column:1/-1; display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:7px; margin-top:4px; }}
    .actions button {{ border:1px solid var(--line); background:#fff; border-radius:14px; padding:9px 6px; font-size:12px; font-weight:900; cursor:pointer; }}
    .actions button.active[data-status="pass"], .pass {{ background:rgba(67,170,109,.13); color:var(--ok); border-color:rgba(67,170,109,.35); }}
    .actions button.active[data-status="fixed_pass"], .fixed_pass {{ background:rgba(88,103,232,.13); color:var(--brand); border-color:rgba(88,103,232,.35); }}
    .actions button.active[data-status="image_error"], .image_error {{ background:rgba(228,88,88,.12); color:var(--bad); border-color:rgba(228,88,88,.35); }}
    .actions button.active[data-status="content_error"], .content_error {{ background:rgba(240,162,46,.15); color:#95610e; border-color:rgba(240,162,46,.35); }}
    textarea {{ grid-column:1/-1; width:100%; min-height:58px; resize:vertical; border:1px solid var(--line); border-radius:15px; padding:10px; outline:none; }}
    aside {{ border-radius:28px; padding:16px; position:sticky; top:18px; height:calc(100vh - 36px); display:grid; grid-template-rows:auto auto minmax(0,1fr) auto; gap:12px; }}
    .progress {{ height:10px; border-radius:999px; background:var(--soft); overflow:hidden; margin-top:10px; }}
    .bar {{ height:100%; width:{pct}%; background:var(--brand); border-radius:inherit; }}
    .counts {{ display:grid; grid-template-columns:1fr 1fr; gap:8px; }}
    .count {{ background:var(--soft); border-radius:18px; padding:12px; }}
    .count strong {{ display:block; font-size:21px; }}
    .count span {{ display:block; color:var(--sub); font-size:11px; font-weight:800; margin-top:2px; }}
    .decision-list {{ overflow:auto; border-top:1px solid var(--line); border-bottom:1px solid var(--line); padding:8px 0; }}
    .decision {{ padding:8px 0; border-top:1px solid var(--line); font-size:12px; }}
    .decision:first-child {{ border-top:0; }}
    .export, .next-batch {{ border:0; border-radius:18px; padding:13px 14px; background:var(--ink); color:white; font-weight:900; cursor:pointer; width:100%; }}
    .next-batch {{ background:var(--brand); margin-bottom:8px; }}
    .export {{ background:var(--soft); color:var(--ink); }}
    .export:disabled, .next-batch:disabled {{ opacity:.42; cursor:not-allowed; }}
    .small {{ color:var(--sub); font-size:12px; line-height:1.35; }}
    a {{ color:var(--brand); text-decoration:none; font-weight:800; }}
    @media (max-width:980px) {{
      .shell {{ grid-template-columns:1fr; }}
      aside {{ position:static; height:auto; }}
      .grid {{ grid-template-columns:1fr; }}
    }}
    @media (max-width:560px) {{
      .shell {{ padding:10px; }}
      header {{ align-items:flex-start; flex-direction:column; }}
      .card {{ grid-template-columns:86px minmax(0,1fr); }}
      .thumb,.empty-thumb {{ width:86px; height:86px; }}
      .actions {{ grid-template-columns:1fr 1fr; }}
    }}
  </style>
</head>
<body>
  <div class="shell">
    <header>
      <div>
        <h1>사장님 DB 검수실</h1>
        <p class="muted">처음부터 10개씩 확인하고, 승인된 항목만 공개 반영 후보가 됩니다.</p>
      </div>
      <div class="summary">
        <span class="pill">현재 배치 {html.escape(str(meta["batch_number"]))}</span>
        <span class="pill">이번 검수 {selected}개</span>
        <span class="pill">전체 {total:,}개</span>
      </div>
    </header>

    <main class="grid" id="cards"></main>

    <aside>
      <section>
        <h2>승인 현황</h2>
        <p class="muted">판정은 이 브라우저에 저장됩니다. 10개를 모두 판정한 뒤 다음 배치로 바로 넘어가면 됩니다.</p>
        <div class="progress"><div class="bar"></div></div>
      </section>
      <section class="counts">
        <div class="count"><strong>{reviewed:,}</strong><span>이미 검수된 항목</span></div>
        <div class="count"><strong>{max(total - reviewed, 0):,}</strong><span>남은 항목</span></div>
        <div class="count"><strong id="approvedCount">0</strong><span>이번 배치 승인</span></div>
        <div class="count"><strong id="blockedCount">0</strong><span>이번 배치 보류</span></div>
      </section>
      <section class="decision-list" id="decisionList"></section>
      <section>
        <button class="next-batch" id="nextBatch">다음 배치 검토하기</button>
        <button class="export" id="export">백업 JSON 저장</button>
        <p class="small" style="margin-top:9px;">검수는 브라우저에서 계속 진행됩니다. 백업 JSON은 나중에 로컬 도구로 승인 후보를 만들 때만 사용합니다.</p>
      </section>
    </aside>
  </div>

  <script id="batch-data" type="application/json">{_json_script(payload)}</script>
  <script>
    const batch = JSON.parse(document.querySelector("#batch-data").textContent);
    const reviewItems = batch.review_items || batch.items;
    const ledgerKey = "deokive-boss-review-ledger-v2";
    const cursorKey = "deokive-boss-review-cursor-v2";
    const labels = batch.meta.allowed_statuses;
    const approved = new Set(batch.meta.approved_statuses);
    const state = JSON.parse(localStorage.getItem(ledgerKey) || "{{}}");
    const cards = document.querySelector("#cards");
    const decisionList = document.querySelector("#decisionList");
    let currentStart = Number(localStorage.getItem(cursorKey) || batch.meta.first_row_index || 0);
    let currentItems = [];

    function nextItemsFrom(start) {{
      return reviewItems
        .filter((item) => item.row_index >= start && !(state[item.row_index] || {{}}).status)
        .slice(0, batch.meta.batch_size);
    }}

    function findNextStart() {{
      const next = reviewItems.find((item) => !(state[item.row_index] || {{}}).status);
      return next ? next.row_index : null;
    }}

    function setCurrentStart(start) {{
      currentStart = start ?? 0;
      localStorage.setItem(cursorKey, String(currentStart));
      currentItems = nextItemsFrom(currentStart);
    }}

    function imageFor(item) {{
      const path = item.local_image_path || item.image_url;
      if (!path) return `<div class="empty-thumb">사진 없음</div>`;
      const src = /^https?:\\/\\//.test(path) ? path : `../../${{path}}`;
      return `<img class="thumb" src="${{src}}" alt="" onerror="this.outerHTML='<div class=&quot;empty-thumb&quot;>사진 로드 실패</div>'">`;
    }}

    function metaLine(label, value) {{
      if (value === null || value === undefined || value === "") return "";
      return `<div><strong>${{label}}</strong> ${{String(value)}}</div>`;
    }}

    function render() {{
      setCurrentStart(currentStart);
      if (!currentItems.length) {{
        cards.innerHTML = `<article class="card" style="grid-column:1/-1; display:block;">
          <div class="title">전체 검수가 완료되었습니다.</div>
          <p class="muted" style="margin-top:8px;">필요하면 백업 JSON을 저장해 로컬 승인 후보 생성 도구에 넣으면 됩니다.</p>
        </article>`;
        renderSide();
        return;
      }}
      cards.innerHTML = currentItems.map((item) => {{
        const decision = state[item.row_index] || {{}};
        const issues = (item.issues || []).map((issue) => `<span class="issue">${{issue}}</span>`).join("");
        return `<article class="card" data-row="${{item.row_index}}">
          ${{imageFor(item)}}
          <div>
            <div class="title">#${{item.row_index}} ${{item.display_name}}</div>
            <div class="meta">
              ${{metaLine("일본어", item.name_ja)}}
              ${{metaLine("시리즈", [item.affiliation, item.series_name, item.sub_series].filter(Boolean).join(" / "))}}
              ${{metaLine("분류", [item.category, item.character_name].filter(Boolean).join(" / "))}}
              ${{metaLine("가격", item.official_price_jpy ? item.official_price_jpy + " JPY" : item.official_price_krw ? item.official_price_krw + " KRW" : "")}}
              ${{item.source_url ? `<div><a href="${{item.source_url}}" target="_blank" rel="noreferrer">출처 열기</a></div>` : ""}}
            </div>
            <div class="issue-row">${{issues || '<span class="issue" style="background:#edf8f1;color:#2d7b4f;">자동 감지 이슈 없음</span>'}}</div>
          </div>
          <div class="actions">
            ${{Object.entries(labels).map(([key, label]) => `<button data-status="${{key}}" class="${{decision.status === key ? 'active' : ''}}">${{label}}</button>`).join("")}}
          </div>
          <textarea placeholder="수정 지시나 오류 내용을 적어주세요.">${{decision.note || ""}}</textarea>
        </article>`;
      }}).join("");

      document.querySelectorAll(".actions button").forEach((button) => {{
        button.addEventListener("click", () => {{
          const card = button.closest(".card");
          const row = card.dataset.row;
          state[row] = state[row] || {{}};
          state[row].status = button.dataset.status;
          state[row].label = labels[button.dataset.status];
          saveFromCards();
          render();
        }});
      }});
      document.querySelectorAll("textarea").forEach((textarea) => {{
        textarea.addEventListener("input", saveFromCards);
      }});
      renderSide();
    }}

    function saveFromCards() {{
      document.querySelectorAll(".card").forEach((card) => {{
        const row = card.dataset.row;
        const textarea = card.querySelector("textarea");
        state[row] = state[row] || {{}};
        state[row].note = textarea.value;
      }});
      localStorage.setItem(ledgerKey, JSON.stringify(state));
      renderSide();
    }}

    function decisions() {{
      return reviewItems
      .filter((item) => (state[item.row_index] || {{}}).status)
      .map((item) => ({{
        row_index: item.row_index,
        catalog_index: item.catalog_index,
        display_name: item.display_name,
        status: (state[item.row_index] || {{}}).status || "",
        status_label: labels[(state[item.row_index] || {{}}).status] || "",
        note: (state[item.row_index] || {{}}).note || ""
      }}));
    }}

    function renderSide() {{
      const rows = decisions();
      const approvedCount = rows.filter((row) => approved.has(row.status)).length;
      const blockedCount = rows.filter((row) => row.status && !approved.has(row.status)).length;
      const pendingCount = Math.max(reviewItems.length - rows.length, 0);
      document.querySelector("#approvedCount").textContent = approvedCount;
      document.querySelector("#blockedCount").textContent = blockedCount;
      document.querySelector(".counts .count:nth-child(1) strong").textContent = rows.length;
      document.querySelector(".counts .count:nth-child(2) strong").textContent = pendingCount;
      decisionList.innerHTML = rows.map((row) => `<div class="decision">
        <strong>#${{row.row_index}} ${{row.status_label || "미판정"}}</strong>
        <span class="small">${{row.display_name}}</span>
      </div>`).join("");
      const everyCurrentDone = currentItems.length > 0 && currentItems.every((item) => (state[item.row_index] || {{}}).status);
      document.querySelector("#nextBatch").disabled = !everyCurrentDone;
    }}

    document.querySelector("#nextBatch").addEventListener("click", () => {{
      saveFromCards();
      const missing = currentItems.filter((item) => !(state[item.row_index] || {{}}).status);
      if (missing.length) {{
        alert("현재 배치 10개를 모두 판정해야 다음 배치로 넘어갈 수 있습니다.");
        return;
      }}
      const nextStart = findNextStart();
      setCurrentStart(nextStart === null ? 0 : nextStart);
      render();
      window.scrollTo({{ top: 0, behavior: "smooth" }});
    }});

    document.querySelector("#export").addEventListener("click", () => {{
      const payload = {{
        meta: {{
          source_batch_first_row_index: batch.meta.first_row_index,
          source_batch_last_row_index: batch.meta.last_row_index,
          exported_scope: "browser_local_review_ledger",
          exported_at: new Date().toISOString(),
          allowed_statuses: labels,
          approved_statuses: batch.meta.approved_statuses
        }},
        decisions: decisions()
      }};
      const blob = new Blob([JSON.stringify(payload, null, 2)], {{ type: "application/json" }});
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = `boss_review_${{batch.meta.first_row_index}}_${{batch.meta.last_row_index}}.json`;
      a.click();
      URL.revokeObjectURL(a.href);
    }});

    render();
  </script>
</body>
</html>
"""


def write_batch(payload: dict[str, Any], json_path: Path, html_path: Path) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    html_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    html_path.write_text(render_html(payload), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a 10-item boss approval review batch for the public catalog.")
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument("--batch-size", type=int, default=10)
    parser.add_argument("--start", type=int)
    parser.add_argument("--out-json", type=Path, default=DEFAULT_BATCH_JSON)
    parser.add_argument("--out-html", type=Path, default=DEFAULT_BATCH_HTML)
    args = parser.parse_args()

    if args.batch_size <= 0:
        raise ValueError("--batch-size must be positive")
    payload = build_batch(
        catalog_path=args.catalog,
        ledger_path=args.ledger,
        batch_size=args.batch_size,
        start=args.start,
    )
    write_batch(payload, args.out_json, args.out_html)
    print(
        json.dumps(
            {
                "out_json": str(args.out_json),
                "out_html": str(args.out_html),
                "selected_items": payload["meta"]["selected_items"],
                "first_row_index": payload["meta"]["first_row_index"],
                "last_row_index": payload["meta"]["last_row_index"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
