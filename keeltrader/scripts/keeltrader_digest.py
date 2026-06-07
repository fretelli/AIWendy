#!/usr/bin/env python3
"""KeelTrader 财富生活方式内容生成器

从 Miniflux wealth 分组获取素材，生成适合小红书的财富行为观察内容，
推送到飞书审核群，人工审核后手动发小红书。

栏目：
  周一  wealth-behavior      财富行为观察
  周二  asset-insight        资产认知
  周四  old-money-mindset    Old Money 思维
  周五  market-psychology    市场与心理
  周日  wealth-weekly-review 本周财富生活方式回顾
"""

import argparse
import base64
import hashlib
import hmac
import json
import logging
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

sys.path.insert(0, "/root/infra-root/scripts/lib")
from xhs_editorial_guard import (  # noqa: E402
    EditorialGuardError,
    format_artifact_summary,
    parse_guard_mode,
    run_guarded_generation,
    source_records_from_entries,
)


# 加载 miniflux .env（共享配置：MINIFLUX_API_URL、LLM、FEISHU）
_MINIFLUX_ENV = Path("/opt/services/miniflux/.env")
if _MINIFLUX_ENV.exists():
    for _line in _MINIFLUX_ENV.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _, _v = _line.partition("=")
            os.environ.setdefault(_k.strip(), _v.strip())

MINIFLUX_API_URL = os.environ["MINIFLUX_API_URL"]
MINIFLUX_API_KEY = os.environ["MINIFLUX_API_KEY"]

LLM_API_BASE = os.environ.get("LLM_API_BASE", "http://23.251.34.157:4000/v1")
LLM_API_KEY  = os.environ.get("LLM_API_KEY",  "sk-litellm-master-a7f3e9b2c4d1")
LLM_MODEL    = os.environ.get("LLM_MODEL",    "deepseek-v3.2")

FEISHU_WEBHOOK_URL    = os.environ["FEISHU_WEBHOOK_URL"]
FEISHU_WEBHOOK_SECRET = os.environ["FEISHU_WEBHOOK_SECRET"]

FLUX_API_URL            = "http://114.66.46.52:16161/v1/images/generations"
FLUX_HEALTH_URL         = "http://114.66.46.52:16161/health"
FEISHU_IMAGE_UPLOAD_URL = "http://127.0.0.1:18081/image/upload"

LOG_FILE = "/var/log/keeltrader-digest.log"
SEEN_STATE_FILE = Path(os.environ.get(
    "KEELTRADER_DIGEST_SEEN_FILE",
    "/root/.cache/keeltrader-digest-seen.json",
))
SEND_STATE_FILE = Path(os.environ.get(
    "KEELTRADER_DIGEST_SEND_STATE_FILE",
    "/root/.cache/keeltrader-digest-send-state.json",
))
SEEN_TTL_HOURS = int(os.environ.get("KEELTRADER_DIGEST_SEEN_TTL_HOURS", "240"))  # 默认 10 天去重
POOL_HOURS = int(os.environ.get("KEELTRADER_DIGEST_POOL_HOURS", "168"))
ENTRY_LIMIT = int(os.environ.get("KEELTRADER_DIGEST_ENTRY_LIMIT", "36"))
FALLBACK_BATCHES = int(os.environ.get("KEELTRADER_DIGEST_FALLBACK_BATCHES", "3"))
EMPTY_ALERT_ENABLED = os.environ.get("KEELTRADER_DIGEST_EMPTY_ALERT_ENABLED", "true").strip().lower() not in {"0", "false", "no", "off"}


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# Wealth RSS feed 识别（按 feed 标题匹配）
# 在 Miniflux 添加以下 feed 时使用这些精确标题
# ──────────────────────────────────────────────
WEALTH_FEED_GROUPS: dict[str, set[str]] = {
    # 与 Miniflux feed 标题精确匹配（大小写不敏感）
    "Robb Report": {"wealth", "asset"},   # 腕表/超跑/游艇/豪宅，资产视角
    "Monocle":     {"wealth", "mindset"}, # 精品生活方式/全球文化/低调富裕
}


# ──────────────────────────────────────────────
# 栏目配置
# ──────────────────────────────────────────────
COLUMN_CONFIGS: dict[str, dict] = {
    "wealth-behavior": {
        "weekday":     0,
        "label":       "财富行为观察",
        "feishu_title": "财富行为观察",
        "prompt_kind": "wealth_behavior",
        "feed_groups": {"wealth", "mindset", "asset"},
        "default_hours": 72,
        "style_mode":  "premium",
    },
    "asset-insight": {
        "weekday":     1,
        "label":       "资产认知",
        "feishu_title": "资产认知",
        "prompt_kind": "asset_insight",
        "feed_groups": {"wealth", "asset"},
        "default_hours": 72,
        "style_mode":  "minimal",
    },
    "old-money-mindset": {
        "weekday":     3,
        "label":       "Old Money 思维",
        "feishu_title": "Old Money 思维",
        "prompt_kind": "old_money_mindset",
        "feed_groups": {"wealth", "mindset"},
        "default_hours": 96,
        "style_mode":  "minimal",
    },
    "market-psychology": {
        "weekday":     4,
        "label":       "市场与心理",
        "feishu_title": "市场与心理",
        "prompt_kind": "market_psychology",
        "feed_groups": {"wealth", "brand"},
        "default_hours": 72,
        "style_mode":  "premium",
    },
    "wealth-weekly-review": {
        "weekday":     6,
        "label":       "本周财富生活方式回顾",
        "feishu_title": "本周财富生活方式回顾",
        "prompt_kind": "wealth_weekly_review",
        "feed_groups": {"wealth", "mindset", "asset", "brand"},
        "default_hours": 168,
        "style_mode":  "premium",
    },
}

MAX_CONTEXT_CHARS = 80000


# ──────────────────────────────────────────────
# Miniflux 数据获取
# ──────────────────────────────────────────────

def _miniflux_get(path: str, params: dict | None = None) -> dict:
    resp = requests.get(
        f"{MINIFLUX_API_URL}/v1{path}",
        headers={"X-Auth-Token": MINIFLUX_API_KEY},
        params=params,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def _strip_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    return re.sub(r"\s+", " ", text).strip()


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)
    except ValueError:
        return None


def _get_feed_groups(feed_title: str) -> set[str]:
    for title, groups in WEALTH_FEED_GROUPS.items():
        if title.lower() in feed_title.lower() or feed_title.lower() in title.lower():
            return groups
    return set()


def fetch_wealth_entries(hours: int) -> list[dict]:
    after_ts = int((datetime.now(timezone.utc) - timedelta(hours=hours)).timestamp())
    raw = []
    offset = 0
    while True:
        data = _miniflux_get("/entries", {
            "order": "published_at", "direction": "desc",
            "after": after_ts, "limit": 100, "offset": offset,
        })
        batch = data.get("entries", [])
        raw.extend(batch)
        if len(batch) < 100:
            break
        offset += 100

    entries = []
    for e in raw:
        feed = e.get("feed", {}) or {}
        feed_title = feed.get("title", "")
        groups = _get_feed_groups(feed_title)
        if not groups:
            continue
        content = e.get("content", "") or ""
        entries.append({
            "title":        e.get("title", "Untitled"),
            "url":          e.get("url", ""),
            "feed_title":   feed_title,
            "published_at": _parse_dt(e.get("published_at")),
            "content_text": _strip_html(content)[:1200],
            "groups":       groups,
        })
    return entries


def filter_by_column(entries: list[dict], config: dict) -> list[dict]:
    target = config["feed_groups"]
    return [e for e in entries if e["groups"] & target]


# ──────────────────────────────────────────────
# 去重（seen state）
# ──────────────────────────────────────────────

def load_seen() -> dict[str, str]:
    if not SEEN_STATE_FILE.exists():
        return {}
    try:
        data = json.loads(SEEN_STATE_FILE.read_text())
        return {str(k): str(v) for k, v in data.items()} if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_seen(data: dict[str, str]):
    SEEN_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    SEEN_STATE_FILE.write_text(json.dumps(data, ensure_ascii=True, indent=2, sort_keys=True))


def load_send_state() -> dict[str, str]:
    if not SEND_STATE_FILE.exists():
        return {}
    try:
        data = json.loads(SEND_STATE_FILE.read_text())
        return {str(k): str(v) for k, v in data.items()} if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_send_state(data: dict[str, str]):
    SEND_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    SEND_STATE_FILE.write_text(json.dumps(data, ensure_ascii=True, indent=2, sort_keys=True))


def prune_and_filter(entries: list[dict], seen: dict[str, str]) -> tuple[list[dict], dict[str, str], int]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=SEEN_TTL_HOURS)
    pruned = {u: t for u, t in seen.items() if (_parse_dt(t) or cutoff) >= cutoff}
    out, dropped = [], 0
    for e in entries:
        if e["url"] in pruned:
            dropped += 1
            continue
        out.append(e)
    if dropped:
        logger.info("去重过滤 %d 篇", dropped)
    return out, pruned, dropped


def mark_seen(entries: list[dict], pruned: dict[str, str]):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    for e in entries:
        if e.get("url"):
            pruned[e["url"]] = now


def entry_batch(entries: list[dict], batch_index: int) -> list[dict]:
    start = max(0, batch_index) * ENTRY_LIMIT
    return entries[start:start + ENTRY_LIMIT]


def _title_tokens(title: str) -> list[str]:
    stop = {
        "the", "and", "for", "with", "from", "that", "this", "into", "luxury",
        "wealth", "market", "markets", "style", "lifestyle", "report", "what",
        "why", "how", "new", "best",
    }
    return [
        token.lower().strip(":-'’")
        for token in re.findall(r"[A-Za-z0-9][A-Za-z0-9'’&:-]{2,}", title)
        if token.lower().strip(":-'’") not in stop
    ]


def _title_name_candidates(title: str) -> list[str]:
    candidates = re.findall(r"《([^》]{2,80})》", title)
    candidates.extend(re.findall(r"\b(?:[A-Z][A-Za-z0-9'’&:-]+(?:\s+|$)){2,6}", title))
    return [re.sub(r"\s+", " ", item).strip(" :-") for item in candidates if len(item.strip()) >= 4]


def extract_used_entries(post_text: str, entries: list[dict]) -> list[dict]:
    normalized_post = post_text.lower()
    post_names = {name.lower() for name in re.findall(r"《([^》]{2,80})》", post_text)}
    used = []
    for entry in entries:
        title = re.sub(r"\s+", " ", str(entry.get("title", ""))).strip()
        if not title:
            continue
        if title.lower() in normalized_post:
            used.append(entry)
            continue
        if any(name.lower() in normalized_post for name in _title_name_candidates(title)):
            used.append(entry)
            continue
        tokens = _title_tokens(title)
        if post_names.intersection(tokens):
            used.append(entry)
            continue
        if tokens and sum(1 for token in tokens if token in normalized_post) >= min(2, len(tokens)):
            used.append(entry)
    return used


# ──────────────────────────────────────────────
# LLM 调用
# ──────────────────────────────────────────────

def _call_llm(prompt: str, temperature: float = 0.6, max_tokens: int = 2000) -> str:
    headers = {"Authorization": f"Bearer {LLM_API_KEY}", "Content-Type": "application/json"}
    payload = {"model": LLM_MODEL, "messages": [{"role": "user", "content": prompt}],
               "temperature": temperature, "max_tokens": max_tokens}
    last_err = None
    for attempt in range(3):
        try:
            resp = requests.post(f"{LLM_API_BASE}/chat/completions",
                                 headers=headers, json=payload, timeout=240)
            resp.raise_for_status()
            text = resp.json()["choices"][0]["message"]["content"].strip()
            if text.startswith("```"):
                text = "\n".join(l for l in text.split("\n") if not l.strip().startswith("```")).strip()
            text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
            text = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"\1", text)
            text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
            return text
        except (requests.Timeout, requests.ConnectionError) as exc:
            last_err = exc
            if attempt < 2:
                time.sleep(2 ** attempt)
        except requests.HTTPError as exc:
            if exc.response is not None and (exc.response.status_code >= 500 or exc.response.status_code == 429):
                last_err = exc
                if attempt < 2:
                    time.sleep(2 ** attempt)
                    continue
            raise
    raise RuntimeError(f"LLM 调用失败: {last_err}")


def build_articles_text(entries: list[dict]) -> str:
    parts = []
    for i, e in enumerate(entries, 1):
        dt = e["published_at"].strftime("%m/%d") if e["published_at"] else "?"
        parts.append(f"[{i}] [{e['feed_title']}] {e['title']} ({dt})\n{e['content_text']}")
    return "\n---\n".join(parts)


# ──────────────────────────────────────────────
# 内容生成（5 种 prompt_kind）
# ──────────────────────────────────────────────

_DEID_RULE = """【具体对象规范（最高优先级）】
1. 允许出现公开报道中的品牌名、城市、产品品类、酒店/餐厅/腕表/车/艺术品/家居等具体对象；这些是小红书搜索和讨论入口。
2. 不要硬广，不要写购买号召，不要堆品牌名单；每个具体对象都必须服务于一个生活方式、资产审美或消费心理观察。
3. 禁止收益承诺、投资建议、目标价、评级、夸张财富叙事和未经素材支持的精确价格。
4. 单一案例也可以写，但必须提炼出普通读者能观察到的品类、场景、审美或行为变化。"""

_TONE_RULE = """【语气规范（严格执行）】
禁止词汇：散户、韭菜、暴富、逆袭、财富自由、翻倍、跑赢
禁止格式：**加粗**、*斜体*、# 标题、- 列表、任何 markdown 符号
禁止 emoji
要求：纯文字段落，平静自信，像一个审美敏感的小红书观察者在写可收藏笔记，不要像私人俱乐部纪要"""

_STYLE_RULE = """【账号风格总规则（高于栏目结构要求）】
- 账号气质必须是：独立、小众、前卫、精品、unique 的财富与生活方式观察，不要写成普通财经号。
- 你像一本独立财富刊物的编辑、审美敏感的小红书观察者、低调但判断精准的生活方式研究者。
- 保留财富分析和行为洞察，但切入口优先来自品味、稀缺性、时间感、代际偏好、消费心理、资产审美和阶层表达。
- 每篇至少提出 1 个不显而易见的主判断，不要复述常见的有钱人标签或鸡汤式财富观。
- 标题要像会被收藏的小红书观察笔记，优先出现具体品类、场景、人群变化或生活方式信号，不要像财经快讯、理财课程、成功学标题。
- 句子要干净、克制、有密度，可以有立场，但不要浮夸，不要故作神秘。
- 尽量避开这类陈词：赛道、风口、逆天、暴击、认知升级、阶层跃迁密码、拿捏、高净值秘籍。
- 不是炫耀财富符号，而是解释为什么某种选择会成为长期品味、关系秩序、资产判断和生活方式的一部分。
- 审美表达不能停在“高级感”，要说明这种审美如何对应判断力、耐心、筛选机制和真实偏好。
- 每篇至少保留 2-4 个具体对象或场景，例如腕表、酒店、餐厅、城市、车、艺术品、家居材质、旅行方式、社交场合。

【中文母语表达规则（严格执行）】
- 英文素材只提供信息，不提供句法；先理解素材，再用中文重新组织句子，不要翻译英文句法。
- 每段优先用人、品牌、酒店、餐厅、消费者、城市、具体场景做主语，少用“趋势、逻辑、变化、审美、信号”等抽象词做主语。
- 禁止连续使用无主句；每段至少 1-2 句要有明确主语。
- 少用“通过、基于、围绕、呈现出、背后是、映射出、对应着、承载着、作为一种、某种意义上”等翻译腔表达。
- 把栏目结构写成自然段，不要在正文里露出“现象 → 逻辑 → 方法”这类箭头结构。
- 多用中文日常表达，例如“我注意到”“你会发现”“这类人现在更愿意”“很多人其实不是在买……而是在看……”。"""


def generate_post(articles_text: str, date_range: str, column: str) -> str:
    config = COLUMN_CONFIGS[column]
    label = config["label"]
    kind  = config["prompt_kind"]

    if kind == "wealth_behavior":
        prompt = f"""{_DEID_RULE}

{_TONE_RULE}

{_STYLE_RULE}

你是一位擅长写生活方式与财富行为的小红书观察者，风格接近 Robb Report 的编辑视角，但表达要更具体、更可讨论。

根据以下近期（{date_range}）素材，写一篇《{label}》。

要求：
- 标题 ≤18 字，像具体发现，不用感叹号
- 空一行后正文 320-420 字
- 按“这周某个具体生活方式/消费场景发生了什么、反映了什么行为逻辑、普通人能借鉴什么观察方法”推进，但必须写成自然段
- 可融入：锚定效应、耐心资本、稀缺性定价、品味作为护城河
- 不要把“有钱人”写成炫耀对象，要通过具体品牌、品类、城市或场景写出更克制、更有筛选力的决策方式
- 结尾 3-4 个 hashtag，具体不泛，优先用品类/场景/人群标签

素材：

{articles_text}

【再次提醒】输出前自检：标题和正文必须具体可感知；可以出现公开品牌/城市/品类，但不能像广告或投资建议。"""
        return _call_llm(prompt, temperature=0.68, max_tokens=1500)

    if kind == "asset_insight":
        prompt = f"""{_DEID_RULE}

{_TONE_RULE}

{_STYLE_RULE}

你是一位了解生活方式资产的小红书观察者。

根据以下近期（{date_range}）素材，写一篇《{label}》。

要求：
- 标题 ≤16 字，像具体发现
- 空一行后正文 260-380 字
- 写人们怎么看腕表、艺术品、房产、收藏品、车、家居、酒店体验——不是作为炫耀，而是作为时间、品味和筛选机制的载体
- 用 1 个具体场景开头，再写 3 个资产审美观察，但必须写成自然段
- 要写出为什么某些实物资产会被视为时间、判断力和审美秩序的容器，而不只是贵
- 结尾 3-4 个具体 hashtag，优先用品类/场景/生活方式标签

素材：

{articles_text}

【再次提醒】可以提公开品牌或品类，但不写价格、型号堆砌和购买建议。"""
        return _call_llm(prompt, temperature=0.60, max_tokens=1200)

    if kind == "old_money_mindset":
        prompt = f"""{_DEID_RULE}

{_TONE_RULE}

{_STYLE_RULE}

你是一位研究低调生活方式、传承型审美和消费选择的小红书观察者。

根据以下近期（{date_range}）素材，写一篇《{label}》。

要求：
- 标题 ≤16 字，像具体生活方式发现
- 空一行后正文 260-380 字
- 写 Old Money 思维和 New Money 的本质差异——不是炫耀差距，而是通过具体服装、旅行、家居、社交、酒店或餐厅场景揭示不同的财富观
- 可写：耐心、品味、低调、长期主义、传承意识、对体验的偏好高于对物品的占有
- 用 1 个具体场景开头，再写 3 个行为差异的观察，但必须写成自然段
- 不要写成刻板人设总结，要写成一套被时间筛出来的生活方式判断
- 结尾 3-4 个具体 hashtag，优先用生活方式/品类/场景词

素材：

{articles_text}"""
        return _call_llm(prompt, temperature=0.62, max_tokens=1200)

    if kind == "market_psychology":
        prompt = f"""{_DEID_RULE}

{_TONE_RULE}

{_STYLE_RULE}

你是一位研究市场情绪和生活方式选择的小红书观察者，为有品味的读者写作。

根据以下近期（{date_range}）素材，写一篇《{label}》。

要求：
- 标题 ≤18 字，像具体发现
- 空一行后正文 320-420 字
- 按“一个可感知的消费/资产/生活方式现象、背后的集体心理机制、懂的人会怎么观察”推进，但必须写成自然段
- 可融入：锚定偏差、羊群效应、过度自信、损失厌恶、确认偏差
- 禁止：买卖建议、具体涨跌幅、板块名称（用"某类资产"代替）
- 不要写成泛心理学科普，要写出真正有判断力的人如何与情绪保持距离
- 结尾 3-4 个具体 hashtag，优先用品类/场景/心理机制词

素材：

{articles_text}

【再次提醒】不提投资品种、机构名、分析师；可以提公开生活方式品牌、品类和场景。"""
        return _call_llm(prompt, temperature=0.65, max_tokens=1500)

    if kind == "wealth_weekly_review":
        prompt = f"""{_DEID_RULE}

{_TONE_RULE}

{_STYLE_RULE}

你是一位写生活方式与财富观察周回顾的小红书内容总编。

根据以下本周（{date_range}）素材，写一篇《{label}》。

要求：
- 标题 ≤20 字
- 空一行后正文 600-800 字
- 固定分 3 段：
  本周哪些生活方式信号变明显 /
  这些信号背后的财富与审美逻辑 /
  普通人可以借鉴哪些观察方法
- 每段有小标题，下面 3-4 句分析
- 每段都要出现具体品牌、城市、品类、场景或消费行为，不要写成纯抽象总结
- 消费者和生活方式视角前置，财富逻辑后置
- 不要写成财经周报，不要平均罗列
- 周回顾要像可收藏的小红书编辑手记，有筛选感和主编判断，而不是摘要合集
- 结尾 4-5 个具体 hashtag，优先用生活方式/品类/城市/场景词

素材：

{articles_text}"""
        return _call_llm(prompt, temperature=0.60, max_tokens=2500)

    raise ValueError(f"未知 prompt_kind: {kind}")


# ──────────────────────────────────────────────
# 图片生成（AI 封面，按 style_mode）
# ──────────────────────────────────────────────

def _image_style(mode: str) -> str:
    styles = {
        "premium": (
            "independent wealth editorial photography, shot on Leica or Hasselblad, "
            "warm ambient light in a private salon, gallery, study, or members-club-like interior, "
            "muted gold, ivory, walnut, and stone palette, cashmere, leather, marble, and brushed metal textures, "
            "quiet understated elegance, niche publication mood, no people, no readable text, no logos"
        ),
        "minimal": (
            "minimal boutique editorial still life on marble, travertine, walnut, or natural stone surface, "
            "soft diffused window light, carefully spaced objects with generous negative space, "
            "warm neutral palette, premium tactile materials, timeless but slightly avant-garde aesthetic, "
            "no people, no text, no brand markings"
        ),
    }
    return styles.get(mode, styles["minimal"])


def _generate_image_prompt(title: str, body: str, mode: str) -> str:
    style = _image_style(mode)
    prompt = f"""根据以下小红书文案，生成一段英文图片 prompt。

要求：
- 输出 60-100 词英文 prompt，描述与文案主题相关的封面图
- 场景必须真实可拍摄，不要抽象概念图
- 风格：{style}
- 包含材质、光线、空间物件描述
- 气质要像 independent wealth magazine / niche lifestyle editorial，而不是通用奢侈品广告
- 禁止文字、数字、图表、Logo、人脸
- 只输出 prompt 文本

文案标题：{title}
文案正文：{body[:300]}"""
    return _call_llm(prompt, temperature=0.5, max_tokens=200)


def _switch_gpu(mode: str) -> bool:
    try:
        r = subprocess.run(
            ["ssh", "hp-omen",
             f"powershell -File C:\\opt\\services\\inference\\switch-mode.ps1 {mode}"],
            capture_output=True, text=True, timeout=120,
        )
        if r.returncode == 0:
            logger.info("GPU 切换成功: %s", mode)
            return True
        logger.warning("GPU 切换失败: %s", r.stderr[:200])
        return False
    except Exception as exc:
        logger.warning("GPU 切换异常: %s", exc)
        return False


def _wait_flux(max_wait: int = 90) -> bool:
    for _ in range(max_wait // 5):
        try:
            if requests.get(FLUX_HEALTH_URL, timeout=5).status_code == 200:
                return True
        except requests.RequestException:
            pass
        time.sleep(5)
    return False


def _generate_cover(title: str, body: str, style_mode: str) -> str | None:
    try:
        img_prompt = _generate_image_prompt(title, body, style_mode)
        if not _switch_gpu("creative"):
            return None
        try:
            if not _wait_flux():
                return None
            resp = requests.post(
                FLUX_API_URL,
                json={"prompt": img_prompt, "size": "1024x1024", "n": 1, "response_format": "b64_json"},
                timeout=120,
            )
            resp.raise_for_status()
            b64 = resp.json()["data"][0]["b64_json"]
            upload = requests.post(FEISHU_IMAGE_UPLOAD_URL, json={"image_base64": b64}, timeout=30)
            upload.raise_for_status()
            body_data = upload.json()
            if body_data.get("code") == 0:
                return body_data["data"]["image_key"]
        finally:
            _switch_gpu("ingest")
    except Exception as exc:
        logger.warning("封面生成失败: %s", exc)
    return None


# ──────────────────────────────────────────────
# 飞书推送
# ──────────────────────────────────────────────

def _feishu_sign() -> tuple[str, str]:
    ts = str(int(time.time()))
    sig = base64.b64encode(
        hmac.new(f"{ts}\n{FEISHU_WEBHOOK_SECRET}".encode(), digestmod=hashlib.sha256).digest()
    ).decode()
    return ts, sig


def _send_text(text: str):
    ts, sig = _feishu_sign()
    payload = {"timestamp": ts, "sign": sig, "msg_type": "text", "content": {"text": text}}
    for attempt in range(4):
        resp = requests.post(FEISHU_WEBHOOK_URL, json=payload, timeout=15)
        resp.raise_for_status()
        body = resp.json()
        if body.get("code") == 0:
            return
        if attempt < 3:
            time.sleep(30 * (2 ** attempt))
            ts, sig = _feishu_sign()
            payload.update({"timestamp": ts, "sign": sig})
    raise RuntimeError(f"飞书推送失败: {body}")


def _send_image(image_key: str):
    ts, sig = _feishu_sign()
    payload = {"timestamp": ts, "sign": sig, "msg_type": "image", "content": {"image_key": image_key}}
    resp = requests.post(FEISHU_WEBHOOK_URL, json=payload, timeout=15)
    resp.raise_for_status()


def _parse_post(text: str) -> tuple[str, str, str]:
    lines = text.strip().split("\n")
    title, body_start = "", 0
    for i, line in enumerate(lines):
        if line.strip():
            title = line.strip()
            body_start = i + 1
            break
    tags_lines, body_end = [], len(lines)
    for i in range(len(lines) - 1, body_start - 1, -1):
        if lines[i].strip() and "#" in lines[i]:
            tags_lines.insert(0, lines[i].strip())
            body_end = i
        elif lines[i].strip():
            break
    return title, "\n".join(lines[body_start:body_end]).strip(), "\n".join(tags_lines)


def send_to_feishu(feishu_title: str, post_text: str, cover_key: str | None):
    title, body, tags = _parse_post(post_text)
    if cover_key:
        _send_image(cover_key)
        time.sleep(1)
    _send_text(f"【{feishu_title}】\n\n📌 标题：\n{title}")
    time.sleep(1)
    _send_text(body)
    time.sleep(1)
    if tags:
        _send_text(tags)


def _send_empty_material_alert(column: str, date_range: str, metrics: dict):
    if not EMPTY_ALERT_ENABLED:
        logger.info("空素材告警已禁用，跳过发送")
        return

    send_state = load_send_state()
    alert_key = f"empty:{column}:{date_range}"
    if send_state.get(alert_key):
        logger.info("空素材告警去重命中，跳过: %s", alert_key)
        return

    config = COLUMN_CONFIGS[column]
    msg = (
        f"【{config['feishu_title']} ({date_range})】\n\n"
        "⚠️ 今日无可用素材，已严格跳过发文（不重复旧内容）\n"
        f"- 栏目: {column}\n"
        f"- Miniflux 原始候选: {metrics.get('raw_entries', 0)}\n"
        f"- 栏目过滤后: {metrics.get('column_entries', 0)}\n"
        f"- 去重过滤: {metrics.get('dropped_by_seen', 0)}\n"
        f"- 最终候选: {metrics.get('final_entries', 0)}\n"
        "- 建议: 补充财富类 RSS 源（Robb Report / Monocle 同类）"
    )
    _send_text(msg)
    send_state[alert_key] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    save_send_state(send_state)


# ──────────────────────────────────────────────
# 主流程
# ──────────────────────────────────────────────

def select_column(args) -> str:
    if args.column:
        return args.column
    if args.auto_mode:
        weekday = datetime.now().weekday()
        for col, cfg in COLUMN_CONFIGS.items():
            if cfg["weekday"] == weekday:
                logger.info("auto-mode: weekday=%d → %s", weekday, col)
                return col
        logger.warning("今日（weekday=%d）无对应栏目", weekday)
        sys.exit(0)
    return "wealth-behavior"


def main():
    parser = argparse.ArgumentParser(description="KeelTrader 财富内容生成器")
    parser.add_argument("--column", choices=sorted(COLUMN_CONFIGS.keys()), default=None)
    parser.add_argument("--auto-mode", action="store_true", help="按星期自动选栏目")
    parser.add_argument("--hours", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true", help="只预览，不推送飞书")
    parser.add_argument("--no-image", action="store_true", help="跳过图片生成")
    parser.add_argument(
        "--editorial-guard",
        choices=["strict", "warn", "off"],
        default=parse_guard_mode(os.environ.get("KEELTRADER_DIGEST_EDITORIAL_GUARD"), "strict"),
        help="资深编辑守门: strict=失败跳过, warn=失败仍输出并标注, off=关闭",
    )
    parser.add_argument(
        "--evidence-timeout",
        type=int,
        default=int(os.environ.get("KEELTRADER_DIGEST_EVIDENCE_TIMEOUT", "25")),
        help="证据采集总超时秒数",
    )
    parser.add_argument(
        "--max-evidence-links",
        type=int,
        default=int(os.environ.get("KEELTRADER_DIGEST_MAX_EVIDENCE_LINKS", "4")),
        help="每篇原文最多跟进的证据外链数量",
    )
    parser.add_argument(
        "--fallback-batches",
        type=int,
        default=FALLBACK_BATCHES,
        help="编辑守门失败后，在同一 7 天素材池内尝试的候选批次数",
    )
    args = parser.parse_args()

    column = select_column(args)
    config = COLUMN_CONFIGS[column]
    hours  = args.hours if args.hours is not None else POOL_HOURS

    logger.info("=" * 50)
    logger.info("KeelTrader Digest 开始 (column=%s, hours=%d, dry_run=%s)", column, hours, args.dry_run)

    # 获取并过滤素材
    all_entries = fetch_wealth_entries(hours)
    entries = filter_by_column(all_entries, config)
    seen = load_seen()
    entries, pruned_seen, dropped_by_seen = prune_and_filter(entries, seen)
    now = datetime.now()
    date_range = f"{(now - timedelta(hours=hours)).strftime('%m/%d')}-{now.strftime('%m/%d')}"
    metrics = {
        "raw_entries": len(all_entries),
        "column_entries": len(filter_by_column(all_entries, config)),
        "dropped_by_seen": dropped_by_seen,
        "final_entries": len(entries),
    }

    if not entries:
        logger.info(
            "无素材，跳过 (column=%s, raw_entries=%d, column_entries=%d, dropped_by_seen=%d)",
            column, metrics["raw_entries"], metrics["column_entries"], metrics["dropped_by_seen"]
        )
        if not args.dry_run:
            _send_empty_material_alert(column, date_range, metrics)
        return

    logger.info("栏目 %s：%d 篇素材", column, len(entries))

    selected_entries = []
    post_text = ""
    guard_artifacts = None
    failures = []
    for batch_index in range(max(1, args.fallback_batches)):
        selected_entries = entry_batch(entries, batch_index)
        if not selected_entries:
            break
        articles_text = build_articles_text(selected_entries)
        logger.info(
            "送入 LLM: batch=%d/%d %d 篇素材, 上下文 %d 字符",
            batch_index + 1, max(1, args.fallback_batches), len(selected_entries), len(articles_text),
        )

        if len(articles_text) > MAX_CONTEXT_CHARS:
            articles_text = articles_text[:MAX_CONTEXT_CHARS]
            logger.warning("素材过长，截断至 %d 字符", MAX_CONTEXT_CHARS)

        try:
            guard_result = run_guarded_generation(
                raw_context=articles_text,
                records=source_records_from_entries(selected_entries),
                generate_post=lambda guarded_context: generate_post(guarded_context, date_range, column),
                llm_call=_call_llm,
                mode=args.editorial_guard,
                domain="财富生活方式、精品消费与市场心理",
                column_label=config["label"],
                date_range=date_range,
                timeout_seconds=args.evidence_timeout,
                max_evidence_links=args.max_evidence_links,
                logger=logger,
            )
            post_text = guard_result.post_text
            guard_artifacts = guard_result.artifacts
            break
        except EditorialGuardError as exc:
            logger.warning("编辑守门失败 (batch=%d): %s", batch_index + 1, exc)
            failures.append((batch_index, exc))
            continue
    if not post_text:
        last_exc = failures[-1][1] if failures else None
        reason = str(last_exc) if last_exc else "无可用候选批次"
        artifacts = last_exc.artifacts if last_exc else None
        msg = f"【{config['feishu_title']} ({date_range})】\n\n今日财富小红书稿待人工核验，已跳过自动正文。\n原因: {reason}\n\n{format_artifact_summary(artifacts)}"
        if args.dry_run:
            print(msg)
        else:
            _send_text(msg)
        return
    logger.info("帖子生成完成 (%d 字)", len(post_text))

    if args.dry_run:
        print(post_text)
        if guard_artifacts:
            print("\n" + format_artifact_summary(guard_artifacts))
        return

    send_state = load_send_state()
    send_key = f"{column}:{date_range}"
    if send_state.get(send_key):
        logger.info("发送去重命中，跳过重复推送: %s", send_key)
        return

    # 生成封面图
    cover_key = None
    if not args.no_image:
        title, body, _ = _parse_post(post_text)
        cover_key = _generate_cover(title, body, config["style_mode"])

    feishu_title = f"{config['feishu_title']} ({date_range})"
    send_to_feishu(feishu_title, post_text, cover_key)
    if guard_artifacts:
        _send_text(format_artifact_summary(guard_artifacts))
    send_state[send_key] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    save_send_state(send_state)

    used_entries = extract_used_entries(post_text, selected_entries)
    if not used_entries:
        logger.warning("未能从正文匹配实际使用素材，回退标记首条候选")
        _send_text(
            f"【{config['feishu_title']} ({date_range})】\n\n"
            "正文使用素材自动匹配失败，已保守只标记首条候选为已用。"
        )
        used_entries = selected_entries[:1]
    mark_seen(used_entries, pruned_seen)
    save_seen(pruned_seen)
    logger.info("标记已用素材 %d/%d 条", len(used_entries), len(selected_entries))

    logger.info("KeelTrader Digest 完成: %s", date_range)
    logger.info("=" * 50)


if __name__ == "__main__":
    main()
