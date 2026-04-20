"""MinerU 文档解析工具（物理子项目特化）。

mode: builder（Build-time only）— 由 Cursor Agent 通过 Shell 调用 CLI 运行。
Harness Runner 没有调用本工具的权限。

调用方式（详见 .cursor/rules/mineru-tool.mdc）：

    # 推荐：本地教材 + vlm + 章节范围
    python -m src.phy.tools.mineru file "res/phy/raw/pep/v1/full.pdf" \\
        --output res/phy/raw/pep/v1/ --model vlm --page-ranges 45-78

    # URL
    python -m src.phy.tools.mineru url "<远程 PDF URL>" \\
        --output res/phy/raw/<source>/ --model vlm --page-ranges 1-30

    # 小章节走免 Token 轻量 API（!! 不返回图片，仅用于纯文本验证）
    python -m src.phy.tools.mineru file "ch3.pdf" \\
        --output res/phy/raw/pep/v1/ --lightweight --page-ranges 1-20

完成后向 stdout 打印一行 JSON 摘要供 ingest 脚本消费：

    {"ok": true, "md": "...", "images_dir": "...", "image_count": 12, "duration_s": 87, ...}
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import shutil
import sys
import time
import zipfile
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

try:
    import requests
except ImportError:  # pragma: no cover
    print(
        "[mineru] 缺少依赖 requests。请先执行：pip install -r requirements.txt",
        file=sys.stderr,
    )
    sys.exit(2)


# ---------------------------------------------------------------------------
# 常量与契约
# ---------------------------------------------------------------------------

API_V4_BASE = "https://mineru.net/api/v4"
API_V1_BASE = "https://mineru.net/api/v1"
ENV_TOKEN_KEY = "MinerU_API_KEY"

DEFAULT_MODEL = "vlm"  # 物理教材默认（公式/受力图密集）
SUPPORTED_MODELS = {"vlm", "pipeline", "MinerU-HTML"}

POLL_INTERVAL_S = 5
POLL_TIMEOUT_S = 30 * 60  # 30 分钟硬上限，超时即视为失败
PAGE_RANGE_SOFT_LIMIT = 30  # 物理子项目软上限（mineru-tool.mdc）。超出仅警告，不阻断

# 错误码 → 中文友好说明 + 建议处理（来自 mineru-tool.mdc）
ERROR_HINTS = {
    "A0202": "Token 无效，请检查 .ENV 中 MinerU_API_KEY 是否过期",
    "A0211": "Token 已过期，请到 mineru.net 重新申请",
    -500: "请求参数错误，检查 Content-Type / 字段类型",
    -10001: "MinerU 服务异常，稍后重试",
    -10002: "请求参数格式错误",
    -60001: "上传 URL 生成失败，稍后重试",
    -60002: "文件格式不支持，请确认后缀（PDF/DOCX/PPTX/PNG/JPG/HTML）",
    -60003: "文件读取失败，可能已损坏，重新导出后再试",
    -60004: "空文件",
    -60005: "文件 > 200MB，需拆分原 PDF 或仅传必要章节",
    -60006: "页数 > 600，必须用 --page-ranges 分段",
    -60007: "模型服务暂不可用，稍后重试",
    -60008: "URL 下载超时，建议改用 file 模式本地上传",
    -60009: "任务队列已满",
    -60010: "解析失败，稍后重试",
    -60011: "未拿到有效文件，确认上传完成",
    -60018: "今日免费配额用尽，明日重试或切 --lightweight",
    -60019: "HTML 解析配额用尽",
    -30001: "轻量接口要求 < 10MB，请切回标准 API",
    -30003: "轻量接口页数超限（< 20 页），请切回标准 API",
}

# 解析 page_ranges 字符串（"45-78" / "2,4-6" / "5"）粗算总页数
RE_RANGE_SEGMENT = re.compile(r"^\s*(\d+)\s*-\s*(\d+)\s*$")


def _estimate_page_count(page_ranges: str) -> Optional[int]:
    """估算 page_ranges 的总页数。无法判断（含 "2--2" 这类语义）时返回 None。"""
    if not page_ranges:
        return None
    total = 0
    for seg in page_ranges.split(","):
        seg = seg.strip()
        if not seg:
            continue
        m = RE_RANGE_SEGMENT.match(seg)
        if m:
            a, b = int(m.group(1)), int(m.group(2))
            if b < a:
                return None
            total += b - a + 1
        elif seg.isdigit():
            total += 1
        else:
            return None
    return total or None


def _warn_if_range_too_wide(page_ranges: Optional[str]) -> None:
    """超 30 页只警告不阻断（mineru-tool.mdc 把 30 页定为软上限）。"""
    if not page_ranges:
        return
    pages = _estimate_page_count(page_ranges)
    if pages is None:
        return
    if pages > PAGE_RANGE_SOFT_LIMIT:
        print(
            f"[mineru] WARN page_ranges={page_ranges} 估算 ≈ {pages} 页 "
            f"> 软上限 {PAGE_RANGE_SOFT_LIMIT}。"
            f"建议拆为多个章节单独 ingest（避免 wiki 拆分粒度失控）。",
            file=sys.stderr,
        )


# Markdown 中图片引用的正则（涵盖 ![](images/x) 与 ![](./images/x) 与 HTML <img>）
RE_MD_IMG = re.compile(r"!\[([^\]]*)\]\(\s*(?:\./)?(?P<path>images/[^\s)]+)\s*\)")
# HTML 同时捕获可选前缀 `./` 与 `images/xxx`，方便整体替换
RE_HTML_IMG = re.compile(
    r"""(?P<full>(?P<quote>["'])(?P<prefix>\./)?(?P<path>images/[^"']+)(?P=quote))"""
)


# ---------------------------------------------------------------------------
# 异常与结果类型
# ---------------------------------------------------------------------------

class MinerUError(RuntimeError):
    """MinerU 调用失败。包装 code 与 friendly hint。"""

    def __init__(self, code, msg: str = "", trace_id: Optional[str] = None) -> None:
        self.code = code
        self.trace_id = trace_id
        hint = ERROR_HINTS.get(code, "未登记错误码，原始信息见 message")
        super().__init__(f"[MinerU code={code}] {msg} | hint={hint} | trace_id={trace_id}")


@dataclass
class ParseResult:
    ok: bool
    md_path: str
    images_dir: str
    image_count: int
    duration_s: float
    api: str  # "standard-v4" | "lightweight-v1"
    model: str
    page_ranges: Optional[str]
    task_id: Optional[str] = None
    batch_id: Optional[str] = None
    raw_zip_url: Optional[str] = None
    notes: list[str] = field(default_factory=list)

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)


# ---------------------------------------------------------------------------
# 鉴权与 HTTP 工具
# ---------------------------------------------------------------------------

def _load_token() -> str:
    """从 .ENV 加载 MinerU_API_KEY，不存在直接退出。"""
    token = os.environ.get(ENV_TOKEN_KEY)
    if token:
        return token.strip()

    env_path = Path(".ENV")
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if line.startswith(f"{ENV_TOKEN_KEY}="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")

    print(
        f"[mineru] 未找到 {ENV_TOKEN_KEY}。请在项目根目录 .ENV 中配置：\n"
        f"    {ENV_TOKEN_KEY}=<your_token>\n"
        f"或导出环境变量后重试。",
        file=sys.stderr,
    )
    sys.exit(3)


def _auth_headers(token: str) -> dict:
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
        "Accept": "*/*",
    }


def _check_response(resp: requests.Response, *, allow_codes: tuple = (0,)) -> dict:
    """统一检查 MinerU 响应：HTTP 200 + body code 在白名单。"""
    if resp.status_code != 200:
        raise MinerUError(
            code=f"HTTP-{resp.status_code}",
            msg=resp.text[:200],
        )
    payload = resp.json()
    code = payload.get("code")
    if code not in allow_codes:
        raise MinerUError(
            code=code,
            msg=payload.get("msg", ""),
            trace_id=payload.get("trace_id"),
        )
    return payload


# ---------------------------------------------------------------------------
# 标准 v4 API：本地文件
# ---------------------------------------------------------------------------

def _v4_request_upload_url(
    token: str,
    file_name: str,
    *,
    model: str,
    page_ranges: Optional[str],
    is_ocr: bool,
    enable_formula: bool,
    enable_table: bool,
    language: str,
) -> tuple[str, str]:
    """申请 OSS 签名上传 URL，返回 (batch_id, upload_url)。"""
    body = {
        "files": [
            {
                "name": file_name,
                "is_ocr": is_ocr,
                **({"page_ranges": page_ranges} if page_ranges else {}),
            }
        ],
        "model_version": model,
        "enable_formula": enable_formula,
        "enable_table": enable_table,
        "language": language,
    }
    resp = requests.post(
        f"{API_V4_BASE}/file-urls/batch",
        headers=_auth_headers(token),
        json=body,
        timeout=60,
    )
    payload = _check_response(resp)
    data = payload["data"]
    return data["batch_id"], data["file_urls"][0]


def _v4_put_file(upload_url: str, local_path: Path) -> None:
    """OSS 签名 URL 直传。**不能带 Content-Type，否则签名不匹配 → 403**。"""
    with local_path.open("rb") as fh:
        resp = requests.put(upload_url, data=fh, timeout=600)
    if resp.status_code != 200:
        raise MinerUError(
            code=f"OSS-PUT-{resp.status_code}",
            msg=f"OSS 直传失败：{resp.text[:200]}",
        )


def _v4_poll_batch(token: str, batch_id: str) -> str:
    """轮询 batch 任务，返回 full_zip_url；失败抛出。"""
    deadline = time.monotonic() + POLL_TIMEOUT_S
    last_state = None
    while time.monotonic() < deadline:
        resp = requests.get(
            f"{API_V4_BASE}/extract-results/batch/{batch_id}",
            headers=_auth_headers(token),
            timeout=30,
        )
        payload = _check_response(resp)
        results = payload["data"].get("extract_result", []) or []
        if not results:
            time.sleep(POLL_INTERVAL_S)
            continue
        item = results[0]
        state = item.get("state")
        if state != last_state:
            print(f"[mineru] batch {batch_id[:8]} state={state}", file=sys.stderr)
            last_state = state
        if state == "done":
            url = item.get("full_zip_url")
            if not url:
                raise MinerUError(code="-noop", msg="state=done 但缺 full_zip_url")
            return url
        if state == "failed":
            raise MinerUError(
                code=item.get("err_code", "failed"),
                msg=item.get("err_msg", "extract failed"),
            )
        time.sleep(POLL_INTERVAL_S)
    raise MinerUError(code="POLL-TIMEOUT", msg=f"轮询超时 ({POLL_TIMEOUT_S}s)")


def _v4_submit_url(
    token: str,
    file_url: str,
    *,
    model: str,
    page_ranges: Optional[str],
    is_ocr: bool,
    enable_formula: bool,
    enable_table: bool,
    language: str,
) -> str:
    """单 URL 提交，返回 task_id。"""
    body = {
        "url": file_url,
        "model_version": model,
        "is_ocr": is_ocr,
        "enable_formula": enable_formula,
        "enable_table": enable_table,
        "language": language,
        **({"page_ranges": page_ranges} if page_ranges else {}),
    }
    resp = requests.post(
        f"{API_V4_BASE}/extract/task",
        headers=_auth_headers(token),
        json=body,
        timeout=60,
    )
    payload = _check_response(resp)
    return payload["data"]["task_id"]


def _v4_poll_task(token: str, task_id: str) -> str:
    deadline = time.monotonic() + POLL_TIMEOUT_S
    last_state = None
    while time.monotonic() < deadline:
        resp = requests.get(
            f"{API_V4_BASE}/extract/task/{task_id}",
            headers=_auth_headers(token),
            timeout=30,
        )
        payload = _check_response(resp)
        data = payload["data"]
        state = data.get("state")
        if state != last_state:
            print(f"[mineru] task {task_id[:8]} state={state}", file=sys.stderr)
            last_state = state
        if state == "done":
            url = data.get("full_zip_url")
            if not url:
                raise MinerUError(code="-noop", msg="state=done 但缺 full_zip_url")
            return url
        if state == "failed":
            raise MinerUError(code="failed", msg=data.get("err_msg", ""))
        time.sleep(POLL_INTERVAL_S)
    raise MinerUError(code="POLL-TIMEOUT", msg=f"轮询超时 ({POLL_TIMEOUT_S}s)")


# ---------------------------------------------------------------------------
# 轻量 v1 API（仅 markdown，无图片）
# ---------------------------------------------------------------------------

def _v1_submit_url(
    file_url: str,
    *,
    page_range: Optional[str],
    enable_formula: bool,
    enable_table: bool,
    is_ocr: bool,
    language: str,
) -> str:
    body = {
        "url": file_url,
        "language": language,
        "enable_table": enable_table,
        "enable_formula": enable_formula,
        "is_ocr": is_ocr,
        **({"page_range": page_range} if page_range else {}),
    }
    resp = requests.post(
        f"{API_V1_BASE}/agent/parse/url",
        json=body,
        timeout=60,
    )
    payload = _check_response(resp)
    return payload["data"]["task_id"]


def _v1_submit_file(
    file_name: str,
    *,
    page_range: Optional[str],
    enable_formula: bool,
    enable_table: bool,
    is_ocr: bool,
    language: str,
) -> tuple[str, str]:
    body = {
        "file_name": file_name,
        "language": language,
        "enable_table": enable_table,
        "enable_formula": enable_formula,
        "is_ocr": is_ocr,
        **({"page_range": page_range} if page_range else {}),
    }
    resp = requests.post(
        f"{API_V1_BASE}/agent/parse/file",
        json=body,
        timeout=60,
    )
    payload = _check_response(resp)
    data = payload["data"]
    return data["task_id"], data["file_url"]


def _v1_poll(task_id: str) -> str:
    """返回 markdown_url；不带图片。"""
    deadline = time.monotonic() + POLL_TIMEOUT_S
    last_state = None
    while time.monotonic() < deadline:
        resp = requests.get(f"{API_V1_BASE}/agent/parse/{task_id}", timeout=30)
        payload = _check_response(resp)
        data = payload["data"]
        state = data.get("state")
        if state != last_state:
            print(f"[mineru-v1] task {task_id[:8]} state={state}", file=sys.stderr)
            last_state = state
        if state == "done":
            return data["markdown_url"]
        if state == "failed":
            raise MinerUError(
                code=data.get("err_code", "failed"),
                msg=data.get("err_msg", ""),
            )
        time.sleep(POLL_INTERVAL_S)
    raise MinerUError(code="POLL-TIMEOUT", msg=f"轮询超时 ({POLL_TIMEOUT_S}s)")


# ---------------------------------------------------------------------------
# 产物落盘：解 zip + 重命名 + 图片迁移 + 路径重写
# ---------------------------------------------------------------------------

def _download_to_bytes(url: str, *, timeout: int = 600) -> bytes:
    resp = requests.get(url, timeout=timeout)
    if resp.status_code != 200:
        raise MinerUError(
            code=f"HTTP-{resp.status_code}",
            msg=f"下载产物失败：{url[:120]}",
        )
    return resp.content


def _rewrite_image_paths(md_text: str, new_dir_name: str) -> str:
    """把 ![](images/x) / <img src="images/x"> 重写为 ![](./<new_dir>/x)。"""

    def md_sub(match: re.Match) -> str:
        alt = match.group(1)
        rel = match.group("path")  # images/xxx
        new_rel = rel.replace("images/", f"{new_dir_name}/", 1)
        return f"![{alt}](./{new_rel})"

    def html_sub(match: re.Match) -> str:
        quote = match.group("quote")
        rel = match.group("path")  # images/xxx
        new_rel = rel.replace("images/", f"{new_dir_name}/", 1)
        return f"{quote}./{new_rel}{quote}"

    md_text = RE_MD_IMG.sub(md_sub, md_text)
    md_text = RE_HTML_IMG.sub(html_sub, md_text)
    return md_text


def _materialize_zip(
    zip_bytes: bytes,
    *,
    output_dir: Path,
    source_stem: str,
) -> tuple[Path, Path, int, list[str]]:
    """解压 zip → 落地。返回 (md_path, images_dir, image_count, notes)。"""
    notes: list[str] = []
    output_dir.mkdir(parents=True, exist_ok=True)
    images_dir = output_dir / f"{source_stem}-images"
    md_path = output_dir / f"{source_stem}.md"

    full_md_text: Optional[str] = None
    image_count = 0

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        names = zf.namelist()
        notes.append(f"zip_entries={len(names)}")

        md_candidates = [n for n in names if n.endswith("full.md") or n.endswith(".md")]
        if not md_candidates:
            raise MinerUError(code="ZIP-NO-MD", msg=f"zip 中未找到 markdown，namelist={names[:10]}")
        md_member = next((n for n in md_candidates if n.endswith("full.md")), md_candidates[0])
        full_md_text = zf.read(md_member).decode("utf-8")

        if images_dir.exists():
            shutil.rmtree(images_dir)
        images_dir.mkdir(parents=True, exist_ok=True)

        for name in names:
            if "images/" in name and not name.endswith("/"):
                target = images_dir / Path(name).name
                with zf.open(name) as src, target.open("wb") as dst:
                    shutil.copyfileobj(src, dst)
                image_count += 1

    if image_count == 0:
        notes.append("zip 内无图片（教材原文可能确无插图，或模型未保留 → 请人工确认）")
    rewritten = _rewrite_image_paths(full_md_text, f"{source_stem}-images")
    md_path.write_text(rewritten, encoding="utf-8")

    return md_path, images_dir, image_count, notes


def _materialize_md_only(
    md_url: str,
    *,
    output_dir: Path,
    source_stem: str,
) -> tuple[Path, Path, int, list[str]]:
    """轻量 API：仅下载 md，images_dir 留空目录占位 + 警告 note。"""
    output_dir.mkdir(parents=True, exist_ok=True)
    images_dir = output_dir / f"{source_stem}-images"
    images_dir.mkdir(parents=True, exist_ok=True)
    md_path = output_dir / f"{source_stem}.md"
    md_text = _download_to_bytes(md_url).decode("utf-8")
    md_path.write_text(md_text, encoding="utf-8")
    return (
        md_path,
        images_dir,
        0,
        ["WARN: 轻量 API 不返回图片，images 目录为空。物理教材正式 ingest 不应使用 lightweight。"],
    )


# ---------------------------------------------------------------------------
# 顶层 parse_* API（供 ingest.py 直接 import 复用）
# ---------------------------------------------------------------------------

def parse_file(
    local_path: str | os.PathLike,
    *,
    output_dir: str | os.PathLike,
    model: str = DEFAULT_MODEL,
    page_ranges: Optional[str] = None,
    lightweight: bool = False,
    is_ocr: bool = False,
    enable_formula: bool = True,
    enable_table: bool = True,
    language: str = "ch",
    allow_full: bool = False,
) -> ParseResult:
    local = Path(local_path).resolve()
    if not local.exists():
        raise FileNotFoundError(f"待解析文件不存在：{local}")
    if model not in SUPPORTED_MODELS:
        raise ValueError(f"model 必须是 {SUPPORTED_MODELS}，当前 {model}")
    if not page_ranges and not allow_full:
        raise ValueError(
            "未传 --page-ranges。物理子项目要求单次解析 ≤ 30 页。"
            "确需全量解析请加 --allow-full（不推荐）。"
        )
    _warn_if_range_too_wide(page_ranges)

    output = Path(output_dir).resolve()
    stem = local.stem
    started = time.monotonic()

    if lightweight:
        print("[mineru] WARN 使用轻量 API：不返回图片，仅适合纯文本验证。", file=sys.stderr)
        task_id, oss_url = _v1_submit_file(
            file_name=local.name,
            page_range=page_ranges,
            enable_formula=enable_formula,
            enable_table=enable_table,
            is_ocr=is_ocr,
            language=language,
        )
        _v4_put_file(oss_url, local)
        md_url = _v1_poll(task_id)
        md_path, images_dir, image_count, notes = _materialize_md_only(
            md_url, output_dir=output, source_stem=stem
        )
        return ParseResult(
            ok=True,
            md_path=str(md_path),
            images_dir=str(images_dir),
            image_count=image_count,
            duration_s=round(time.monotonic() - started, 1),
            api="lightweight-v1",
            model="pipeline-lite",
            page_ranges=page_ranges,
            task_id=task_id,
            notes=notes,
        )

    token = _load_token()
    batch_id, oss_url = _v4_request_upload_url(
        token,
        file_name=local.name,
        model=model,
        page_ranges=page_ranges,
        is_ocr=is_ocr,
        enable_formula=enable_formula,
        enable_table=enable_table,
        language=language,
    )
    _v4_put_file(oss_url, local)
    zip_url = _v4_poll_batch(token, batch_id)
    zip_bytes = _download_to_bytes(zip_url)
    md_path, images_dir, image_count, notes = _materialize_zip(
        zip_bytes, output_dir=output, source_stem=stem
    )
    return ParseResult(
        ok=True,
        md_path=str(md_path),
        images_dir=str(images_dir),
        image_count=image_count,
        duration_s=round(time.monotonic() - started, 1),
        api="standard-v4",
        model=model,
        page_ranges=page_ranges,
        batch_id=batch_id,
        raw_zip_url=zip_url,
        notes=notes,
    )


def parse_url(
    file_url: str,
    *,
    output_dir: str | os.PathLike,
    source_stem: Optional[str] = None,
    model: str = DEFAULT_MODEL,
    page_ranges: Optional[str] = None,
    lightweight: bool = False,
    is_ocr: bool = False,
    enable_formula: bool = True,
    enable_table: bool = True,
    language: str = "ch",
    allow_full: bool = False,
) -> ParseResult:
    if model not in SUPPORTED_MODELS:
        raise ValueError(f"model 必须是 {SUPPORTED_MODELS}，当前 {model}")
    if not page_ranges and not allow_full:
        raise ValueError(
            "未传 --page-ranges。物理子项目要求单次解析 ≤ 30 页。"
            "确需全量解析请加 --allow-full（不推荐）。"
        )
    _warn_if_range_too_wide(page_ranges)

    if source_stem is None:
        source_stem = Path(file_url.split("?", 1)[0]).stem or "remote"
    output = Path(output_dir).resolve()
    started = time.monotonic()

    if lightweight:
        print("[mineru] WARN 使用轻量 API：不返回图片，仅适合纯文本验证。", file=sys.stderr)
        task_id = _v1_submit_url(
            file_url,
            page_range=page_ranges,
            enable_formula=enable_formula,
            enable_table=enable_table,
            is_ocr=is_ocr,
            language=language,
        )
        md_url = _v1_poll(task_id)
        md_path, images_dir, image_count, notes = _materialize_md_only(
            md_url, output_dir=output, source_stem=source_stem
        )
        return ParseResult(
            ok=True,
            md_path=str(md_path),
            images_dir=str(images_dir),
            image_count=image_count,
            duration_s=round(time.monotonic() - started, 1),
            api="lightweight-v1",
            model="pipeline-lite",
            page_ranges=page_ranges,
            task_id=task_id,
            notes=notes,
        )

    token = _load_token()
    task_id = _v4_submit_url(
        token,
        file_url,
        model=model,
        page_ranges=page_ranges,
        is_ocr=is_ocr,
        enable_formula=enable_formula,
        enable_table=enable_table,
        language=language,
    )
    zip_url = _v4_poll_task(token, task_id)
    zip_bytes = _download_to_bytes(zip_url)
    md_path, images_dir, image_count, notes = _materialize_zip(
        zip_bytes, output_dir=output, source_stem=source_stem
    )
    return ParseResult(
        ok=True,
        md_path=str(md_path),
        images_dir=str(images_dir),
        image_count=image_count,
        duration_s=round(time.monotonic() - started, 1),
        api="standard-v4",
        model=model,
        page_ranges=page_ranges,
        task_id=task_id,
        raw_zip_url=zip_url,
        notes=notes,
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="mineru",
        description="MinerU 文档解析（物理子项目特化，Builder-only）",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--output", required=True, help="产物输出目录（md + 图片子目录的父目录）")
    common.add_argument("--model", default=DEFAULT_MODEL, choices=sorted(SUPPORTED_MODELS))
    common.add_argument(
        "--page-ranges",
        help='单次解析页范围，如 "1-30" 或 "2,4-6"。物理子项目要求 ≤ 30 页',
    )
    common.add_argument("--lightweight", action="store_true", help="使用免 Token 轻量 API（不返图）")
    common.add_argument("--is-ocr", action="store_true", help="开启 OCR")
    common.add_argument("--no-formula", action="store_true", help="关闭公式识别（不推荐）")
    common.add_argument("--no-table", action="store_true", help="关闭表格识别")
    common.add_argument("--language", default="ch")
    common.add_argument(
        "--allow-full",
        action="store_true",
        help="允许不传 --page-ranges 全量解析（违反物理子项目规则，仅紧急用）",
    )

    pf = sub.add_parser("file", parents=[common], help="解析本地文件")
    pf.add_argument("path", help="本地文件路径")

    pu = sub.add_parser("url", parents=[common], help="解析远程 URL")
    pu.add_argument("file_url", help="远程文件 URL")
    pu.add_argument("--source-stem", help="自定义产物文件 stem（不传则从 URL 推断）")

    return p


def _emit_result(result: ParseResult) -> None:
    """最后一行输出 JSON 摘要，方便上游 ingest 脚本管道消费。"""
    print(
        f"[mineru] OK md={result.md_path} images={result.image_count} "
        f"({result.images_dir}) api={result.api} model={result.model} "
        f"duration={result.duration_s}s",
        file=sys.stderr,
    )
    for note in result.notes:
        print(f"[mineru] note: {note}", file=sys.stderr)
    print(result.to_json())


def main(argv: Optional[list[str]] = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        if args.cmd == "file":
            result = parse_file(
                args.path,
                output_dir=args.output,
                model=args.model,
                page_ranges=args.page_ranges,
                lightweight=args.lightweight,
                is_ocr=args.is_ocr,
                enable_formula=not args.no_formula,
                enable_table=not args.no_table,
                language=args.language,
                allow_full=args.allow_full,
            )
        else:
            result = parse_url(
                args.file_url,
                output_dir=args.output,
                source_stem=args.source_stem,
                model=args.model,
                page_ranges=args.page_ranges,
                lightweight=args.lightweight,
                is_ocr=args.is_ocr,
                enable_formula=not args.no_formula,
                enable_table=not args.no_table,
                language=args.language,
                allow_full=args.allow_full,
            )
    except MinerUError as exc:
        print(f"[mineru] FAIL {exc}", file=sys.stderr)
        print(json.dumps({"ok": False, "error": str(exc), "code": str(exc.code)}, ensure_ascii=False))
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"[mineru] FAIL {type(exc).__name__}: {exc}", file=sys.stderr)
        print(json.dumps({"ok": False, "error": f"{type(exc).__name__}: {exc}"}, ensure_ascii=False))
        return 1
    _emit_result(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
