#!/usr/bin/env python3
"""Fetch public wiki nodes. Python 3.10+, standard library only."""
import argparse
import base64
import copy
import hashlib
import html
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import parse_qsl, quote, unquote, urlsplit
from urllib.request import Request, urlopen

SLUG = quote("v2ray免费账号", safe="")
SOURCES = {
    "github": {
        "name": "GitHub",
        "url": f"https://github.com/Alvin9999-newpac/fanqiang/wiki/{SLUG}",
        "content_url": f"https://raw.githubusercontent.com/wiki/Alvin9999-newpac/fanqiang/{SLUG}.md",
    },
    "gitlab": {
        "name": "GitLab",
        "url": f"https://gitlab.com/zhifan999/fq/-/wikis/{SLUG}",
        "content_url": f"https://gitlab.com/api/v4/projects/zhifan999%2Ffq/wikis/{SLUG}",
    },
}
MAX_BYTES = 4 * 1024 * 1024
CST = timezone(timedelta(hours=8))


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def timestamp(value):
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.timestamp() if parsed.tzinfo else 0
    except (ValueError, TypeError, AttributeError):
        return 0


def request_text(url, attempts=3):
    if urlsplit(url).scheme != "https":
        raise ValueError("数据地址必须使用 HTTPS")
    for attempt in range(attempts):
        try:
            req = Request(url, headers={"User-Agent": "NodeUpdateHelper/1.0", "Accept": "*/*", "Cache-Control": "no-cache"})
            with urlopen(req, timeout=20) as response:
                data = response.read(MAX_BYTES + 1)
                if len(data) > MAX_BYTES:
                    raise ValueError("响应过大")
                return data.decode("utf-8-sig")
        except Exception:
            if attempt == attempts - 1:
                raise
            time.sleep(2 ** attempt)


class EditTimeParser(HTMLParser):
    """Only use the page header / this wiki's versions section, never global times."""
    def __init__(self, source):
        super().__init__()
        self.source = source
        self.stack = []
        self.times = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        own_scope = (self.source == "github" and "gh-header-meta" in attrs.get("class", "").split()) or (
            self.source == "gitlab" and attrs.get("id") == "versions")
        active = own_scope or any(entry[1] for entry in self.stack)
        if active and tag in ("relative-time", "time") and timestamp(attrs.get("datetime")):
            self.times.append(attrs["datetime"])
        if tag not in {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}:
            self.stack.append((tag, active))

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                break


def parse_edit_time(source, page):
    parser = EditTimeParser(source)
    parser.feed(page)
    if not parser.times:
        raise ValueError("未找到 Wiki 最后编辑时间，页面结构可能已改变")
    return max(parser.times, key=timestamp)


def plain(text):
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    return html.unescape(re.sub(r"<[^>]*>", "", text).replace("**", "").replace("`", "")).strip()


def parse_author_time(markdown):
    # Anchor on update labels; don't mistake an old incident date for an update.
    for line in markdown.splitlines():
        clean = plain(line).lstrip("# ")
        if not re.match(r"(?:最后)?更新时间\s*[:：]", clean):
            continue
        value = re.split(r"[:：]", clean, maxsplit=1)[1].strip()
        match = re.search(r"(20\d{2})[年/-](\d{1,2})[月/-](\d{1,2})日?(?:[ T]*(\d{1,2})[点时:：](\d{1,2})?分?)?", value)
        if not match:
            return {"raw": value, "iso": None, "precision": None}
        y, month, day, hour, minute = match.groups()
        try:
            dt = datetime(int(y), int(month), int(day), int(hour or 0), int(minute or 0), tzinfo=CST)
            return {"raw": value, "iso": dt.isoformat(), "precision": "minute" if hour else "day"}
        except ValueError:
            return {"raw": value, "iso": None, "precision": None}
    return {"raw": None, "iso": None, "precision": None}


def heading(line):
    stripped = line.strip()
    if not (re.match(r"#{1,6}\s", stripped) or (stripped.startswith("**") and stripped.endswith("**"))):
        return None
    text = plain(re.sub(r"^#{1,6}\s*", "", stripped))
    return re.fullmatch(r"(?:🚀\s*)?节点\s*([12])\s*(?:[（(]([^）)]+)[）)])?\s*(一键导入链接)?\s*[:：]?", text)


def canonical_link(link):
    scheme = link.split(":", 1)[0].lower()
    if scheme == "vmess":
        raw = link.split("://", 1)[1]
        obj = json.loads(base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4)))
        if not isinstance(obj, dict) or not all(obj.get(k) for k in ("add", "port", "id")):
            raise ValueError("VMess 链接缺少地址、端口或用户 ID")
        obj.pop("ps", None)  # Human-readable remarks aren't connection parameters.
        return {"scheme": scheme, "config": {k: str(v) if isinstance(v, (int, float)) else v for k, v in obj.items()}}
    parsed = urlsplit(link)
    if not parsed.netloc or not parsed.hostname:
        raise ValueError("导入链接缺少服务器地址")
    # Preserve credentials and all query fields; only discard display name and query order.
    return {"scheme": scheme, "authority": parsed.netloc, "path": parsed.path,
            "query": sorted(parse_qsl(parsed.query, keep_blank_values=True))}


def parse_nodes(markdown):
    lines = markdown.replace("\r\n", "\n").splitlines()
    sections = []
    fenced = False
    for index, line in enumerate(lines):
        if re.match(r"^\s*(`{3,}|~{3,})", line):
            fenced = not fenced
            continue
        match = None if fenced else heading(line)
        if match and not match.group(3):
            sections.append((index, match))
    nodes = []
    for number in ("1", "2"):
        candidates = [(pos, m) for pos, m in sections if m.group(1) == number]
        if len(candidates) != 1:
            raise ValueError(f"节点{number}标题缺失或重复")
        start, title = candidates[0]
        end = next((pos for pos, _ in sections if pos > start), len(lines))
        section = lines[start + 1:end]
        import_at = next((i for i, line in enumerate(section) if (m := heading(line)) and m.group(1) == number and m.group(3)), None)
        if import_at is None:
            raise ValueError(f"节点{number}缺少一键导入链接标题")
        # End import subsection at the next formatted heading / horizontal rule.
        link_lines = []
        for line in section[import_at + 1:]:
            if re.match(r"^\s*(?:#{1,6}\s|\*\*[^*]|\*{3,}\s*$|---+\s*$)", line):
                break
            link_lines.append(line)
        links = re.findall(r"(?:vmess|vless|anytls|trojan|ss|ssr|hysteria2|hysteria|hy2|tuic)://[^\s`<>\"\)]+", "\n".join(link_lines), flags=re.I)
        links = list(dict.fromkeys(html.unescape(link) for link in links))
        if len(links) != 1:
            raise ValueError(f"节点{number}导入链接缺失或不唯一")
        link = links[0]
        normalized = canonical_link(link)
        fields = []
        notes = []
        for line in section[:import_at]:
            if line.strip().startswith("|"):
                cells = [plain(c) for c in re.split(r"(?<!\\)\|", line.strip().strip("|"))]
                if len(cells) >= 2 and cells[0] != "节点参数" and not re.fullmatch(r"[:\s-]+", cells[0]):
                    fields.append({"label": cells[0], "value": cells[1].replace(r"\|", "|")})
            elif line.strip():
                notes.append(plain(line))
        if not fields:
            raise ValueError(f"节点{number}参数表缺失，暂不覆盖上次完整数据")
        # Include parameter values as well as link config, tolerate label spacing.
        params = {re.sub(r"\s+", "", field["label"]): field["value"] for field in fields}
        fingerprint = hashlib.sha256(json.dumps({"link": normalized, "fields": params}, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        nodes.append({"id": int(number), "name": f"节点{number}", "protocol": link.split(":", 1)[0].lower(),
                      "fields": fields, "notes": "\n".join(notes), "import_url": link, "fingerprint": fingerprint})
    return nodes


def fetch_source(key, previous=None, fetch=request_text):
    config = SOURCES[key]
    result = {"id": key, **config, "status": "error", "stale": False, "checked_at": now_iso(),
              "last_success_at": None, "page_edited_at": None, "page_edit_url": config["url"] + ("/history" if key == "gitlab" else ""),
              "author_updated": {"raw": None, "iso": None, "precision": None}, "nodes": [], "warnings": [], "error": None}
    try:
        raw = fetch(config["content_url"])
        markdown = json.loads(raw)["content"] if key == "gitlab" else raw
        result["nodes"] = parse_nodes(markdown)
        result["author_updated"] = parse_author_time(markdown)
        try:
            result["page_edited_at"] = parse_edit_time(key, fetch(result["page_edit_url"]))
        except Exception as exc:
            result["warnings"].append(f"编辑时间获取失败：{type(exc).__name__}: {exc}")
        if result["author_updated"]["raw"] and not result["author_updated"]["iso"]:
            result["warnings"].append("作者时间格式未识别，保留原文")
        result["status"] = "partial" if result["warnings"] else "ok"
        result["last_success_at"] = now_iso()
    except Exception as exc:
        if previous and len(previous.get("nodes", [])) == 2:
            for field in ("nodes", "author_updated", "page_edited_at", "last_success_at"):
                result[field] = copy.deepcopy(previous.get(field))
            result["stale"] = True
        result["error"] = f"{type(exc).__name__}: {exc}"
    return result


def summarize(sources):
    usable = [s for s in sources if len(s.get("nodes", [])) == 2]
    fresh = [s for s in usable if not s["stale"] and s["status"] in ("ok", "partial")]
    pool = fresh or usable
    comparison = {"status": "unknown", "nodes": {}, "includes_stale": any(s["stale"] for s in usable)}
    if len(usable) == 2:
        for i in (1, 2):
            fingerprints = [next(n["fingerprint"] for n in s["nodes"] if n["id"] == i) for s in usable]
            comparison["nodes"][str(i)] = fingerprints[0] == fingerprints[1]
        comparison["status"] = "same" if all(comparison["nodes"].values()) else "different"
    if not pool:
        return comparison, {"source_id": None, "basis": None, "uncertain": True, "stale": False, "reason": "暂无可复制的节点，请等待后台成功抓取。"}
    # Use the same kind of time for both sources; never compare author time to page time.
    if all(timestamp(s.get("author_updated", {}).get("iso")) for s in pool):
        basis = "author"
        rank = lambda s: timestamp(s["author_updated"]["iso"])
    elif all(timestamp(s.get("page_edited_at")) for s in pool):
        basis = "page"
        rank = lambda s: timestamp(s["page_edited_at"])
    else:
        basis = "unknown"
        rank = lambda s: 0
    chosen = max(pool, key=rank)
    tied = len(pool) > 1 and len({rank(s) for s in pool}) == 1
    # A date-only update represents a whole day, not a known midnight update.
    overlap = False
    if basis == "author" and len(pool) > 1:
        intervals = [(rank(s), rank(s) + (86400 if s["author_updated"].get("precision") == "day" else 60)) for s in pool]
        overlap = max(start for start, _ in intervals) < min(end for _, end in intervals)
    uncertain = (basis == "unknown" or tied or overlap) and comparison["status"] != "same" and len(pool) > 1
    if len(pool) == 1:
        reason = "当前仅此来源有可用数据，无法确认另一来源是否更新。"
    elif comparison["status"] == "same":
        reason = "两站节点参数与导入配置一致，可任选来源。"
    elif uncertain:
        reason = "两站内容不同，时间相同或不完整；暂选此来源，无法确定哪站更新。"
    else:
        reason = "按较晚的作者更新时间选择。" if basis == "author" else "作者时间不完整，按较晚的网页编辑时间选择。"
    if not fresh:
        reason = "本次两站均未获取成功，以下仅为上次成功数据。" + reason
    return comparison, {"source_id": chosen["id"], "basis": basis, "uncertain": uncertain,
                        "stale": chosen["stale"], "reason": reason}


def valid_snapshot(data):
    if not isinstance(data, dict) or data.get("schema_version") != 1 or not isinstance(data.get("sources"), list):
        return False
    seen = set()
    for source in data["sources"]:
        if not isinstance(source, dict) or source.get("id") not in SOURCES or source["id"] in seen:
            return False
        seen.add(source["id"])
        if not isinstance(source.get("author_updated"), dict) or not isinstance(source.get("nodes"), list):
            return False
        nodes = source["nodes"]
        if nodes and (len(nodes) != 2 or not all(isinstance(n, dict) for n in nodes) or {n.get("id") for n in nodes} != {1, 2}):
            return False
        for node in nodes:
            if not all(isinstance(node.get(key), str) for key in ("name", "protocol", "import_url", "fingerprint")) or not isinstance(node.get("fields"), list):
                return False
    return True


def update(output, previous_url=None):
    old = {}
    try:
        candidate = json.loads(output.read_text())
        if valid_snapshot(candidate):
            old = candidate
    except (OSError, ValueError):
        pass
    if previous_url:
        try:
            candidate = json.loads(request_text(previous_url, attempts=1))
            if valid_snapshot(candidate) and timestamp(candidate.get("checked_at")) > timestamp(old.get("checked_at")):
                old = candidate
        except Exception as exc:
            print(f"Previous Pages snapshot unavailable: {type(exc).__name__}")
    previous = {s["id"]: s for s in old.get("sources", [])}
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda key: fetch_source(key, previous.get(key)), SOURCES))
    comparison, latest = summarize(results)
    data = {"schema_version": 1, "checked_at": now_iso(), "interval_minutes": 30,
            "sources": results, "comparison": comparison, "latest": latest}
    output.parent.mkdir(parents=True, exist_ok=True)
    temp = output.with_suffix(".tmp")
    serialized = json.dumps(data, ensure_ascii=False, indent=2)
    temp.write_text(serialized + "\n", encoding="utf-8")
    temp.replace(output)
    # A classic script fallback lets non-technical users preview index.html via file://.
    # The deployed app still fetches no-store data.json and uses this only as initial data.
    js_output = output.with_suffix(".js")
    js_temp = js_output.with_suffix(".tmp")
    safe_serialized = serialized.replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    js_temp.write_text(f"window.__NODE_DATA__ = {safe_serialized};\n", encoding="utf-8")
    js_temp.replace(js_output)
    for source in results:
        print(f"{source['name']}: {source['status']}, stale={source['stale']}, nodes={len(source['nodes'])}")
    return data


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parents[1] / "site/data.json")
    parser.add_argument("--previous-url", help="Previously deployed HTTPS data.json, used with local snapshot as recovery")
    args = parser.parse_args()
    update(args.output, args.previous_url)
