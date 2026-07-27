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
    "pass": "통과",
}
APPROVED_STATUSES = {"pass"}


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
    data = _json_script(payload)
    template = r"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Deokive Boss Review</title>
  <style>
    :root {
      --ink:#1d1d1f; --sub:#69707c; --line:#e6e8ee; --paper:#fff; --back:#f5f6f8;
      --brand:#5867e8; --ok:#2f9d66; --warn:#d98a19; --bad:#d94f4f; --soft:#eef2f7;
      font-family:-apple-system,BlinkMacSystemFont,"SF Pro Display","Segoe UI",sans-serif;
      color-scheme:light;
    }
    * { box-sizing:border-box; }
    body { margin:0; min-height:100vh; background:var(--back); color:var(--ink); }
    button, textarea { font:inherit; }
    .shell { width:min(1280px,100%); margin:0 auto; padding:18px; display:grid; grid-template-columns:minmax(0,1fr) 360px; gap:16px; }
    header, aside, .card, .handoff { background:rgba(255,255,255,.96); border:1px solid var(--line); box-shadow:0 18px 42px rgba(24,28,38,.08); }
    header { grid-column:1/-1; border-radius:28px; padding:16px 18px; display:flex; justify-content:space-between; gap:14px; align-items:center; }
    h1,h2,h3,p { margin:0; letter-spacing:0; }
    h1 { font-size:23px; }
    .muted { color:var(--sub); font-size:13px; line-height:1.35; margin-top:4px; }
    .summary { display:flex; gap:8px; flex-wrap:wrap; justify-content:flex-end; }
    .pill { padding:8px 10px; border-radius:999px; background:var(--soft); font-size:12px; font-weight:900; white-space:nowrap; }
    .grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:12px; }
    .card { border-radius:24px; padding:14px; display:grid; grid-template-columns:112px minmax(0,1fr); gap:13px; min-height:210px; }
    .thumb { width:112px; height:112px; border-radius:18px; background:var(--soft); border:1px solid var(--line); object-fit:cover; }
    .empty-thumb { width:112px; height:112px; border-radius:18px; background:var(--soft); display:grid; place-items:center; color:var(--sub); font-size:12px; font-weight:900; text-align:center; padding:10px; }
    .title { font-size:15px; line-height:1.25; font-weight:900; word-break:keep-all; overflow-wrap:anywhere; }
    .meta { margin-top:8px; display:grid; gap:4px; color:var(--sub); font-size:12px; line-height:1.3; }
    .issue-row { display:flex; flex-wrap:wrap; gap:5px; margin-top:8px; }
    .issue { padding:5px 7px; border-radius:999px; background:#fff3db; color:#92600f; font-size:11px; font-weight:900; }
    .actions { grid-column:1/-1; display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:7px; margin-top:4px; }
    .actions button { border:1px solid var(--line); background:#fff; border-radius:14px; padding:9px 6px; font-size:12px; font-weight:900; cursor:pointer; }
    .actions button.active[data-status="pass"], .pass { background:rgba(47,157,102,.13); color:var(--ok); border-color:rgba(47,157,102,.35); }
    .actions button.active[data-status="image_error"], .image_error { background:rgba(217,79,79,.12); color:var(--bad); border-color:rgba(217,79,79,.35); }
    .actions button.active[data-status="content_error"], .content_error { background:rgba(217,138,25,.15); color:#95610e; border-color:rgba(217,138,25,.35); }
    textarea { grid-column:1/-1; width:100%; min-height:58px; resize:vertical; border:1px solid var(--line); border-radius:15px; padding:10px; outline:none; }
    aside { border-radius:28px; padding:16px; position:sticky; top:18px; height:calc(100vh - 36px); display:grid; grid-template-rows:auto auto minmax(0,1fr) auto; gap:12px; }
    .progress { height:10px; border-radius:999px; background:var(--soft); overflow:hidden; margin-top:10px; }
    .bar { height:100%; width:__PCT__%; background:var(--brand); border-radius:inherit; }
    .batch-status { margin-top:9px; padding:10px 11px; border-radius:16px; background:#f8f9fc; border:1px solid var(--line); color:var(--sub); font-size:12px; line-height:1.35; font-weight:800; }
    .counts { display:grid; grid-template-columns:1fr 1fr; gap:8px; }
    .count { background:var(--soft); border-radius:18px; padding:12px; }
    .count strong { display:block; font-size:21px; }
    .count span { display:block; color:var(--sub); font-size:11px; font-weight:800; margin-top:2px; }
    .decision-list { overflow:auto; border-top:1px solid var(--line); border-bottom:1px solid var(--line); padding:8px 0; }
    .decision { padding:8px 0; border-top:1px solid var(--line); font-size:12px; }
    .decision:first-child { border-top:0; }
    .next-batch, .secondary { border:0; border-radius:18px; padding:13px 14px; font-weight:900; cursor:pointer; width:100%; }
    .next-batch { background:var(--brand); color:white; margin-bottom:8px; }
    .secondary { background:var(--soft); color:var(--ink); }
    .next-batch:disabled, .secondary:disabled { opacity:.42; cursor:not-allowed; }
    .small { color:var(--sub); font-size:12px; line-height:1.35; }
    .handoff { grid-column:1/-1; border-radius:24px; padding:14px; display:none; }
    .handoff.show { display:block; }
    .handoff-grid { display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-top:10px; }
    .worker { border:1px solid var(--line); border-radius:18px; background:#f9fafc; padding:12px; }
    .worker strong { display:block; font-size:14px; }
    pre { max-height:190px; overflow:auto; white-space:pre-wrap; word-break:break-word; background:#111318; color:white; border-radius:16px; padding:12px; font-size:11px; line-height:1.45; }
    a { color:var(--brand); text-decoration:none; font-weight:800; }
    @media (max-width:980px) {
      .shell { grid-template-columns:1fr; }
      aside { position:static; height:auto; }
      .grid { grid-template-columns:1fr; }
      .handoff-grid { grid-template-columns:1fr; }
    }
    @media (max-width:560px) {
      .shell { padding:10px; }
      header { align-items:flex-start; flex-direction:column; }
      .card { grid-template-columns:86px minmax(0,1fr); }
      .thumb,.empty-thumb { width:86px; height:86px; }
      .actions { grid-template-columns:1fr 1fr; }
    }
  </style>
</head>
<body>
  <div class="shell">
    <header>
      <div>
        <h1>사장님 DB 검수실</h1>
        <p class="muted">10개씩 판정하면 수정 담당과 공개 반영 담당에게 나눠 넘기는 큐가 만들어집니다.</p>
      </div>
      <div class="summary">
        <span class="pill">현재 배치 __BATCH_NUMBER__</span>
        <span class="pill">이번 검수 __SELECTED__개</span>
        <span class="pill" id="localProgressPill">브라우저 검수 0/__TOTAL__</span>
        <span class="pill">전체 __TOTAL__개</span>
      </div>
    </header>

    <main class="grid" id="cards"></main>

    <aside>
      <section>
        <h2>승인 현황</h2>
        <p class="muted">판정은 브라우저에 저장됩니다. 현재 10개를 모두 판정해야 다음 배치로 이동할 수 있습니다.</p>
        <div class="progress"><div class="bar"></div></div>
        <div class="batch-status" id="batchStatus">현재 배치 상태를 불러오는 중입니다.</div>
      </section>
      <section class="counts">
        <div class="count"><strong id="reviewedCount">0</strong><span>브라우저 검수</span></div>
        <div class="count"><strong id="pendingCount">__TOTAL__</strong><span>남은 항목</span></div>
        <div class="count"><strong id="approvedCount">0</strong><span>반영 담당 큐</span></div>
        <div class="count"><strong id="blockedCount">0</strong><span>수정 담당 큐</span></div>
      </section>
      <section class="decision-list" id="decisionList"></section>
      <section>
        <button class="next-batch" id="nextBatch">다음 배치 검토하기</button>
        <button class="secondary" id="copyHandoff" disabled>방금 넘긴 작업 JSON 복사</button>
        <p class="small" style="margin-top:9px;">사진오류/내용오류는 수정 담당에게, 통과는 공개 반영 담당에게 들어갑니다.</p>
      </section>
    </aside>

    <section class="handoff" id="handoffPanel">
      <h2>작업자에게 넘긴 이번 배치</h2>
      <p class="muted">이 블록이 떠야 정상입니다. JSON을 복사해서 나에게 주면 수정 담당 1명과 반영 담당 1명으로 나눠 처리할 수 있습니다.</p>
      <div class="handoff-grid">
        <div class="worker"><strong>수정 담당</strong><span class="small" id="reworkSummary">대기 없음</span></div>
        <div class="worker"><strong>공개 반영 담당</strong><span class="small" id="publishSummary">대기 없음</span></div>
      </div>
      <pre id="handoffJson"></pre>
    </section>
  </div>

  <script id="batch-data" type="application/json">__DATA__</script>
  <script>
    const batch = JSON.parse(document.querySelector("#batch-data").textContent);
    const reviewItems = batch.review_items || batch.items;
    const ledgerKey = "deokive-boss-review-ledger-v3";
    const cursorKey = "deokive-boss-review-cursor-v3";
    const handoffKey = "deokive-boss-review-handoffs-v1";
    const labels = batch.meta.allowed_statuses;
    const approved = new Set(batch.meta.approved_statuses);
    const state = JSON.parse(localStorage.getItem(ledgerKey) || "{}");
    const cards = document.querySelector("#cards");
    const decisionList = document.querySelector("#decisionList");
    let lastHandoff = null;
    let currentStart = Number(localStorage.getItem(cursorKey) || batch.meta.first_row_index || 0);
    let currentItems = [];

    function nextItemsFrom(start) {
      return reviewItems
        .filter((item) => item.row_index >= start)
        .slice(0, batch.meta.batch_size);
    }

    function findNextStart() {
      const next = reviewItems.find((item) => !normalizeDecisionState(state[item.row_index] || {}).statuses.length);
      return next ? next.row_index : null;
    }

    function setCurrentStart(start) {
      currentStart = start ?? 0;
      localStorage.setItem(cursorKey, String(currentStart));
      currentItems = nextItemsFrom(currentStart);
    }

    function escapeText(value) {
      return String(value ?? "").replace(/[&<>"']/g, (char) => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
      })[char]);
    }

    function imageFor(item) {
      const path = item.local_image_path || item.image_url;
      if (!path) return `<div class="empty-thumb">사진 없음</div>`;
      const src = /^https?:\/\//.test(path) ? path : `../../${path}`;
      return `<img class="thumb" src="${escapeText(src)}" alt="" onerror="this.outerHTML='<div class=&quot;empty-thumb&quot;>사진 로드 실패</div>'">`;
    }

    function metaLine(label, value) {
      if (value === null || value === undefined || value === "") return "";
      return `<div><strong>${escapeText(label)}</strong> ${escapeText(value)}</div>`;
    }

    function render() {
      setCurrentStart(currentStart);
      if (!currentItems.length) {
        cards.innerHTML = `<article class="card" style="grid-column:1/-1; display:block;">
          <div class="title">전체 검수가 완료되었습니다.</div>
          <p class="muted" style="margin-top:8px;">검수 기록은 이 브라우저에 저장되어 있습니다.</p>
        </article>`;
        renderSide();
        return;
      }
      cards.innerHTML = currentItems.map((item) => {
        const decision = normalizeDecisionState(state[item.row_index] || {});
        state[item.row_index] = decision;
        const issues = (item.issues || []).map((issue) => `<span class="issue">${escapeText(issue)}</span>`).join("");
        const series = [item.affiliation, item.series_name, item.sub_series].filter(Boolean).join(" / ");
        const category = [item.category, item.character_name].filter(Boolean).join(" / ");
        const price = item.official_price_jpy ? `${item.official_price_jpy} JPY` : item.official_price_krw ? `${item.official_price_krw} KRW` : "";
        return `<article class="card" data-row="${item.row_index}">
          ${imageFor(item)}
          <div>
            <div class="title">#${item.row_index} ${escapeText(item.display_name)}</div>
            <div class="meta">
              ${metaLine("일본어", item.name_ja)}
              ${metaLine("시리즈", series)}
              ${metaLine("분류", category)}
              ${metaLine("가격", price)}
              ${item.source_url ? `<div><a href="${escapeText(item.source_url)}" target="_blank" rel="noreferrer">출처 열기</a></div>` : ""}
            </div>
            <div class="issue-row">${issues || '<span class="issue" style="background:#edf8f1;color:#2d7b4f;">자동 감지 이슈 없음</span>'}</div>
          </div>
          <div class="actions">
            ${Object.entries(labels).map(([key, label]) => `<button data-status="${key}" class="${decision.statuses.includes(key) ? 'active' : ''}">${escapeText(label)}</button>`).join("")}
          </div>
          <textarea placeholder="수정 지시나 오류 내용을 적어주세요.">${escapeText(decision.note || "")}</textarea>
        </article>`;
      }).join("");

      document.querySelectorAll(".actions button").forEach((button) => {
        button.addEventListener("click", () => {
          const card = button.closest(".card");
          const row = card.dataset.row;
          const selected = button.dataset.status;
          const decision = normalizeDecisionState(state[row] || {});
          if (selected === "pass") {
            decision.statuses = decision.statuses.includes("pass") ? [] : ["pass"];
          } else {
            decision.statuses = decision.statuses.filter((status) => status !== "pass");
            if (decision.statuses.includes(selected)) {
              decision.statuses = decision.statuses.filter((status) => status !== selected);
            } else {
              decision.statuses.push(selected);
            }
          }
          decision.status = primaryStatus(decision.statuses);
          decision.status_label = statusLabels(decision.statuses).join(" + ");
          state[row] = decision;
          saveFromCards();
          render();
        });
      });
      document.querySelectorAll("textarea").forEach((textarea) => {
        textarea.addEventListener("input", saveFromCards);
      });
      renderSide();
    }

    function saveFromCards() {
      document.querySelectorAll(".card[data-row]").forEach((card) => {
        const row = card.dataset.row;
        const textarea = card.querySelector("textarea");
        state[row] = normalizeDecisionState(state[row] || {});
        state[row].note = textarea.value;
      });
      localStorage.setItem(ledgerKey, JSON.stringify(state));
      renderSide();
    }

    function normalizeDecisionState(decision) {
      const statuses = Array.isArray(decision.statuses)
        ? decision.statuses
        : decision.status
          ? [decision.status]
          : [];
      const allowed = statuses.filter((status) => labels[status]);
      const normalized = allowed.includes("pass")
        ? ["pass"]
        : [...new Set(allowed.filter((status) => status !== "pass"))];
      return {
        ...decision,
        statuses: normalized,
        status: primaryStatus(normalized),
        status_label: statusLabels(normalized).join(" + ")
      };
    }

    function primaryStatus(statuses) {
      if (statuses.includes("pass")) return "pass";
      if (statuses.includes("image_error")) return "image_error";
      if (statuses.includes("content_error")) return "content_error";
      return "";
    }

    function statusLabels(statuses) {
      return statuses.map((status) => labels[status]).filter(Boolean);
    }

    function decisions(items = reviewItems) {
      return items
        .filter((item) => normalizeDecisionState(state[item.row_index] || {}).statuses.length)
        .map((item) => ({
          ...(() => {
            const decision = normalizeDecisionState(state[item.row_index] || {});
            return {
              statuses: decision.statuses,
              status: decision.status,
              status_label: decision.status_label
            };
          })(),
          row_index: item.row_index,
          catalog_index: item.catalog_index,
          display_name: item.display_name,
          note: (state[item.row_index] || {}).note || "",
          source_url: item.source_url || "",
          image_url: item.image_url || "",
          local_image_path: item.local_image_path || "",
          name_ko: item.name_ko || "",
          name_ja: item.name_ja || "",
          category: item.category || "",
          character_name: item.character_name || ""
        }));
    }

    function makeHandoff(batchItems) {
      const rows = decisions(batchItems);
      const rework = rows.filter((row) => !approved.has(row.status)).map((row) => ({
        ...row,
        assigned_to: "수정 담당",
        required_action: row.statuses.includes("image_error") && row.statuses.includes("content_error")
          ? "사진/출처와 내용 둘 다 수정 후 다시 사장 검수로 제출"
          : row.statuses.includes("image_error")
            ? "사진/출처 수정 후 다시 사장 검수로 제출"
            : "내용 수정 후 다시 사장 검수로 제출"
      }));
      const publish = rows.filter((row) => approved.has(row.status)).map((row) => ({
        ...row,
        assigned_to: "공개 반영 담당",
        required_action: "승인 DB 후보에 반영"
      }));
      return {
        meta: {
          exported_scope: "one_completed_boss_review_batch",
          batch_first_row_index: batchItems[0]?.row_index ?? null,
          batch_last_row_index: batchItems[batchItems.length - 1]?.row_index ?? null,
          exported_at: new Date().toISOString(),
          worker_flow: ["수정 담당", "공개 반영 담당"],
          approved_statuses: batch.meta.approved_statuses
        },
        decisions: rows,
        rework_agent_queue: rework,
        publish_agent_queue: publish
      };
    }

    function showHandoff(payload) {
      lastHandoff = payload;
      const panel = document.querySelector("#handoffPanel");
      panel.classList.add("show");
      document.querySelector("#reworkSummary").textContent = `${payload.rework_agent_queue.length}개 대기`;
      document.querySelector("#publishSummary").textContent = `${payload.publish_agent_queue.length}개 대기`;
      document.querySelector("#handoffJson").textContent = JSON.stringify(payload, null, 2);
      document.querySelector("#copyHandoff").disabled = false;
    }

    function renderSide() {
      const rows = decisions();
      const approvedCount = rows.filter((row) => approved.has(row.status)).length;
      const blockedCount = rows.filter((row) => row.status && !approved.has(row.status)).length;
      const pendingCount = Math.max(reviewItems.length - rows.length, 0);
      const currentDoneCount = currentItems.filter((item) => normalizeDecisionState(state[item.row_index] || {}).statuses.length).length;
      const browserPct = reviewItems.length ? Math.round((rows.length / reviewItems.length) * 10000) / 100 : 0;
      document.querySelector("#approvedCount").textContent = approvedCount;
      document.querySelector("#blockedCount").textContent = blockedCount;
      document.querySelector("#reviewedCount").textContent = rows.length;
      document.querySelector("#pendingCount").textContent = pendingCount;
      document.querySelector("#localProgressPill").textContent = `브라우저 검수 ${rows.length.toLocaleString()}/${reviewItems.length.toLocaleString()}`;
      document.querySelector(".bar").style.width = `${browserPct}%`;
      decisionList.innerHTML = rows.slice(-60).reverse().map((row) => `<div class="decision">
        <strong>#${row.row_index} ${escapeText(row.status_label || "미판정")}</strong>
        <span class="small">${escapeText(row.display_name)}</span>
      </div>`).join("");
      const everyCurrentDone = currentItems.length > 0 && currentItems.every((item) => normalizeDecisionState(state[item.row_index] || {}).statuses.length);
      document.querySelector("#nextBatch").disabled = !everyCurrentDone;
      if (!currentItems.length) {
        document.querySelector("#batchStatus").textContent = `전체 ${reviewItems.length.toLocaleString()}개 검수가 완료되었습니다.`;
      } else {
        const first = currentItems[0].row_index;
        const last = currentItems[currentItems.length - 1].row_index;
        document.querySelector("#batchStatus").textContent = `현재 배치 #${first}-${last} · ${currentDoneCount}/${currentItems.length}개 판정 완료`;
      }
    }

    document.querySelector("#nextBatch").addEventListener("click", () => {
      saveFromCards();
      const completedBatch = currentItems.slice();
      const missing = completedBatch.filter((item) => !normalizeDecisionState(state[item.row_index] || {}).statuses.length);
      if (missing.length) {
        alert("현재 배치 10개를 모두 판정해야 다음 배치로 넘어갈 수 있습니다.");
        return;
      }
      const handoffs = JSON.parse(localStorage.getItem(handoffKey) || "[]");
      const payload = makeHandoff(completedBatch);
      handoffs.push(payload);
      localStorage.setItem(handoffKey, JSON.stringify(handoffs));
      showHandoff(payload);
      const nextStart = findNextStart();
      setCurrentStart(nextStart === null ? 0 : nextStart);
      render();
      window.scrollTo({ top: 0, behavior: "smooth" });
    });

    document.querySelector("#copyHandoff").addEventListener("click", async () => {
      if (!lastHandoff) return;
      const text = JSON.stringify(lastHandoff, null, 2);
      try {
        await navigator.clipboard.writeText(text);
        document.querySelector("#copyHandoff").textContent = "복사 완료";
        setTimeout(() => document.querySelector("#copyHandoff").textContent = "방금 넘긴 작업 JSON 복사", 1200);
      } catch {
        alert("브라우저 보안 때문에 자동 복사가 막혔습니다. 아래 JSON을 직접 선택해서 복사해주세요.");
      }
    });

    render();
  </script>
</body>
</html>
"""
    return (
        template.replace("__PCT__", str(pct))
        .replace("__DATA__", data)
        .replace("__BATCH_NUMBER__", html.escape(str(meta["batch_number"])))
        .replace("__SELECTED__", html.escape(str(selected)))
        .replace("__TOTAL__", html.escape(f"{total:,}"))
    )


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
