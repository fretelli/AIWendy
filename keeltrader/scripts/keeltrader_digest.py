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

_DEID_RULE = """【去识别化规范（最高优先级）】
1. 全文禁止出现任何具体品牌名、公司名、人名、产品型号
2. 禁止精确数字（价格、融资额、市值、门店数）
3. 抽象成行为规律、趋势、逻辑，不是单一案例复述
4. 单一企业素材无法泛化时，直接丢弃"""

_TONE_RULE = """【语气规范（严格执行）】
禁止词汇：散户、韭菜、暴富、逆袭、财富自由、翻倍、跑赢
禁止格式：**加粗**、*斜体*、# 标题、- 列表、任何 markdown 符号
禁止 emoji
要求：纯文字段落，平静自信，像在私人俱乐部和聪明朋友聊天"""

_STYLE_RULE = """【账号风格总规则（高于栏目结构要求）】
- 账号气质必须是：独立、小众、前卫、精品、unique 的财富与生活方式观察，不要写成普通财经号。
- 你像一本独立财富刊物的编辑、审美敏感的资产观察者、低调但判断精准的生活方式研究者。
- 保留财富分析和行为洞察，但切入口优先来自品味、稀缺性、时间感、代际偏好、消费心理、资产审美和阶层表达。
- 每篇至少提出 1 个不显而易见的主判断，不要复述常见的有钱人标签或鸡汤式财富观。
- 标题要像会被收藏的独立观察笔记，不要像财经快讯、理财课程、成功学标题。
- 句子要干净、克制、有密度，可以有立场，但不要浮夸，不要故作神秘。
- 尽量避开这类陈词：赛道、风口、逆天、暴击、认知升级、阶层跃迁密码、拿捏、高净值秘籍。
- 不是炫耀财富符号，而是解释为什么某种选择会成为长期品味、关系秩序、资产判断和生活方式的一部分。
- 审美表达不能停在“高级感”，要说明这种审美如何对应判断力、耐心、筛选机制和真实偏好。"""


def generate_post(articles_text: str, date_range: str, column: str) -> str:
    config = COLUMN_CONFIGS[column]
    label = config["label"]
    kind  = config["prompt_kind"]

    if kind == "wealth_behavior":
        prompt = f"""{_DEID_RULE}

{_TONE_RULE}

{_STYLE_RULE}

你是一位为高净值读者写作的财富行为观察者，风格接近 Robb Report 的编辑视角。

根据以下近期（{date_range}）素材，写一篇《{label}》。

要求：
- 标题 ≤18 字，有品味感，不用感叹号
- 空一行后正文 320-420 字
- 结构：这周有钱人的财富决策里发生了什么 → 背后反映的行为逻辑 → 对想进入这个层次的人的真实启示
- 可融入：锚定效应、耐心资本、稀缺性定价、品味作为护城河
- 不要把“有钱人”写成炫耀对象，要写成一套更克制、更有筛选力的决策方式
- 结尾 3-4 个 hashtag，具体不泛（#独立精品投资逻辑 而非 #投资）

素材：

{articles_text}

【再次提醒】输出前自检，任何一段让读者猜得出具体品牌或人物，就重写。"""
        return _call_llm(prompt, temperature=0.68, max_tokens=1500)

    if kind == "asset_insight":
        prompt = f"""{_DEID_RULE}

{_TONE_RULE}

{_STYLE_RULE}

你是一位了解有钱人如何看待实物资产的观察者。

根据以下近期（{date_range}）素材，写一篇《{label}》。

要求：
- 标题 ≤16 字
- 空一行后正文 260-380 字
- 写有钱人怎么看腕表、艺术品、房产、收藏品——不是作为炫耀，而是作为资产和品味的载体
- 结构：1 个核心认知 + 3 个具体的资产逻辑观察
- 要写出为什么某些实物资产会被视为时间、判断力和审美秩序的容器，而不只是贵
- 结尾 3-4 个 hashtag

素材：

{articles_text}

【再次提醒】不提具体品牌、价格、型号。"""
        return _call_llm(prompt, temperature=0.60, max_tokens=1200)

    if kind == "old_money_mindset":
        prompt = f"""{_DEID_RULE}

{_TONE_RULE}

{_STYLE_RULE}

你是一位研究 Old Money 文化和传承型财富的观察者。

根据以下近期（{date_range}）素材，写一篇《{label}》。

要求：
- 标题 ≤16 字
- 空一行后正文 260-380 字
- 写 Old Money 思维和 New Money 的本质差异——不是炫耀差距，而是揭示一种不同的财富观
- 可写：耐心、品味、低调、长期主义、传承意识、对体验的偏好高于对物品的占有
- 结构：1 个核心对比 + 3 个行为差异的观察
- 不要写成刻板人设总结，要写成一套被时间筛出来的生活方式判断
- 结尾 3-4 个 hashtag

素材：

{articles_text}"""
        return _call_llm(prompt, temperature=0.62, max_tokens=1200)

    if kind == "market_psychology":
        prompt = f"""{_DEID_RULE}

{_TONE_RULE}

{_STYLE_RULE}

你是一位研究市场情绪和投资行为的观察者，为有品味的读者写作。

根据以下近期（{date_range}）素材，写一篇《{label}》。

要求：
- 标题 ≤18 字
- 空一行后正文 320-420 字
- 结构：这周市场在发生什么 → 背后的集体心理机制 → 懂的人会怎么思考
- 可融入：锚定偏差、羊群效应、过度自信、损失厌恶、确认偏差
- 禁止：买卖建议、具体涨跌幅、板块名称（用"某类资产"代替）
- 不要写成泛心理学科普，要写出真正有判断力的人如何与情绪保持距离
- 结尾 3-4 个 hashtag

素材：

{articles_text}

【再次提醒】不提任何具体的投资品种、机构名、分析师。"""
        return _call_llm(prompt, temperature=0.65, max_tokens=1500)

    if kind == "wealth_weekly_review":
        prompt = f"""{_DEID_RULE}

{_TONE_RULE}

{_STYLE_RULE}

你是一位为高净值读者写周度回顾的内容总编。

根据以下本周（{date_range}）素材，写一篇《{label}》。

要求：
- 标题 ≤20 字
- 空一行后正文 600-800 字
- 固定分 3 段：
  本周有钱人在关注什么 /
  这些关注背后的财富逻辑 /
  哪些思维方式值得普通人借鉴
- 每段有小标题，下面 3-4 句分析
- 消费者和生活方式视角前置，财富逻辑后置
- 不要写成财经周报，不要平均罗列
- 周回顾要像独立财富刊物的编辑手记，有筛选感和主编判断，而不是摘要合集
- 结尾 4-5 个 hashtag

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
    args = parser.parse_args()

    column = select_column(args)
    config = COLUMN_CONFIGS[column]
    hours  = args.hours if args.hours is not None else config["default_hours"]

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

    articles_text = build_articles_text(entries)

    if len(articles_text) > MAX_CONTEXT_CHARS:
        articles_text = articles_text[:MAX_CONTEXT_CHARS]
        logger.warning("素材过长，截断至 %d 字符", MAX_CONTEXT_CHARS)

    post_text = generate_post(articles_text, date_range, column)
    logger.info("帖子生成完成 (%d 字)", len(post_text))

    if args.dry_run:
        print(post_text)
        return

    send_state = load_send_state()
    send_key = f"send:{column}:{date_range}"
    if send_state.get(send_key):
        logger.info("发送去重命中，跳过: %s", send_key)
        return

    # 生成封面图
    cover_key = None
    if not args.no_image:
        title, body, _ = _parse_post(post_text)
        cover_key = _generate_cover(title, body, config["style_mode"])

    feishu_title = f"{config['feishu_title']} ({date_range})"
    send_to_feishu(feishu_title, post_text, cover_key)
    send_state[send_key] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    save_send_state(send_state)

    mark_seen(entries, pruned_seen)
    save_seen(pruned_seen)

    logger.info("KeelTrader Digest 完成: %s", date_range)
    logger.info("=" * 50)


if __name__ == "__main__":
    main()
