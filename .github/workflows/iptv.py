import os
import aiohttp
import asyncio
import time
import json
from collections import defaultdict, Counter
import re
from datetime import datetime, timedelta
from typing import Dict, Iterable, List, Optional, Set, Tuple, Any

# ==================== 原代码中的动态关键词过滤 ====================
def get_dynamic_keywords():
    today = datetime.now().strftime("%Y-%m-%d")
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    fixed_keywords = ["免费提供", "独家", "最新", "稳定", today, tomorrow]
    return fixed_keywords

def contains_date(text):
    date_pattern = r"\d{4}-\d{2}-\d{2}"
    return re.search(date_pattern, text) is not None

# ==================== 从新代码中引入的增强归一化 & 匹配 ====================
CHAR_NORMALIZATION_MAP = str.maketrans({
    "頻": "频", "視": "视", "臺": "台", "綜": "综", "聞": "闻", "體": "体",
    "藝": "艺", "經": "经", "濟": "济", "娛": "娱", "樂": "乐", "電": "电",
    "廣": "广", "畫": "画", "劇": "剧", "紀": "纪", "錄": "录", "網": "网",
    "導": "导", "髮": "发", "衛": "卫", "陰": "阴", "陽": "阳", "麗": "丽",
    "龍": "龙", "鄉": "乡", "鎮": "镇", "區": "区", "縣": "县", "灣": "湾",
    "滬": "沪", "閩": "闽", "贛": "赣", "蘇": "苏", "浙": "浙", "魯": "鲁",
    "豫": "豫", "鄂": "鄂", "湘": "湘", "粵": "粤", "瓊": "琼", "渝": "渝",
    "遼": "辽", "寧": "宁", "貴": "贵", "雲": "云", "藏": "藏", "陝": "陕",
    "晉": "晋", "冀": "冀", "錫": "锡",
})

def normalize_text_for_match(text: str) -> str:
    normalized = text.translate(CHAR_NORMALIZATION_MAP).strip().upper().replace("＋", "+")
    normalized = re.sub(r"[ \t\r\n\-_|·•:：,，.。/\\()\[\]【】「」'\"`]+", "", normalized)
    return normalized

PROVINCE_ALIASES = {
    "北京": {"北京台"}, "上海": {"上海台", "东方明珠", "沪上"}, "天津": {"天津台"},
    "重庆": {"重庆台"}, "河北": {"河北台"}, "山西": {"山西台", "三晋"}, "辽宁": {"辽宁台", "辽沈"},
    "吉林": {"吉林台"}, "内蒙": {"内蒙古"}, "黑龙江": {"龙江", "黑龙江台"}, "江苏": {"江苏台", "苏南"},
    "浙江": {"浙江台", "之江"}, "安徽": {"安徽台"}, "福建": {"福建台", "八闽"}, "江西": {"江西台"},
    "山东": {"山东台", "齐鲁"}, "河南": {"河南台", "中原"}, "湖北": {"湖北台"}, "湖南": {"湖南台"},
    "广东": {"广东台", "南粤"}, "广西": {"广西台"}, "海南": {"海南台"}, "四川": {"四川台", "巴蜀"},
    "贵州": {"贵州台"}, "云南": {"云南台", "七彩云南"}, "西藏": {"西藏台"}, "陕西": {"陕西台", "三秦"},
    "甘肃": {"甘肃台", "陇原"}, "青海": {"青海台"}, "宁夏": {"宁夏台"}, "新疆": {"新疆台"},
}

COMMON_CHANNEL_SUFFIXES = (
    "新闻综合频道", "新闻综合", "新闻频道", "新聞綜合頻道", "新聞綜合", "新聞頻道",
    "社会民生频道", "社会民生", "社會民生頻道", "社會民生", "影视娱乐频道", "影视娱乐",
    "影視娛樂頻道", "影視娛樂", "经济生活频道", "经济生活", "經濟生活頻道", "經濟生活",
    "文体旅游频道", "文体旅游", "文體旅遊頻道", "文體旅遊", "文旅频道", "文旅", "文旅頻道",
    "旅游频道", "旅游", "旅遊頻道", "旅遊", "体育频道", "体育", "體育頻道", "體育",
    "教育频道", "教育", "教育頻道", "少儿频道", "少儿", "少兒頻道", "少兒",
    "科教频道", "科教", "科教頻道", "文化影视", "文化娱乐", "文化生活", "文化频道", "文化",
    "文化影視", "文化娛樂", "文化頻道", "都市频道", "都市", "都市頻道", "民生频道", "民生",
    "民生頻道", "资讯频道", "资讯", "資訊頻道", "資訊", "公共频道", "公共", "公共頻道",
    "综合频道", "综合", "綜合頻道", "娱乐频道", "娱乐", "娛樂頻道", "影视", "影視",
    "导视频道", "导视", "導視頻道", "導視", "生活频道", "生活頻道", "文艺频道", "文艺",
    "文藝頻道", "文藝", "法治频道", "法治頻道", "军事频道", "軍事頻道", "电视台", "電視台",
    "频道", "頻道", "直播", "高清", "超清", "标清",
)

NON_GEO_TOKENS = {
    "新闻", "综合", "公共", "生活", "民生", "都市", "经济", "科教", "教育", "少儿",
    "影视", "娱乐", "体育", "文旅", "旅游", "文化", "资讯", "导视", "频道", "电视",
    "法治", "军事", "党建", "购物", "健康", "养生", "时尚", "美食", "游戏", "电竞",
    "戲曲", "戏曲", "戲劇", "戏剧", "曲艺", "紀錄", "纪录", "綜藝", "综艺", "台", "TV",
    "HD", "SD", "UHD", "FHD", "4K", "8K",
}

COMMON_CHANNEL_SUFFIXES_NORMALIZED = tuple(
    sorted({normalize_text_for_match(s) for s in COMMON_CHANNEL_SUFFIXES}, key=len, reverse=True)
)
NON_GEO_TOKENS_NORMALIZED = {normalize_text_for_match(token) for token in NON_GEO_TOKENS}

PROVINCE_SUFFIXES = ("特别行政区", "维吾尔自治区", "壮族自治区", "回族自治区", "自治区", "省", "市")
AREA_SUFFIXES = ("自治县", "自治州", "自治区", "特别行政区", "新区", "开发区", "高新区",
                 "地区", "林区", "矿区", "县", "市", "区", "州", "盟", "旗", "镇", "乡", "街道")
IGNORED_GEO_NAMES = {"市辖区", "城区", "郊区", "新区", "开发区", "高新区", "矿区", "城区街道",
                     "其他", "直辖", "省直辖县级行政区划", "自治区直辖县级行政区划",
                     "市辖县", "县级市", "直辖县级", "工业园区", "示范区", "合作区", "管理区"}
IGNORED_GEO_NAMES_NORMALIZED = {normalize_text_for_match(name) for name in IGNORED_GEO_NAMES}

ONLINE_GEO_DATA_URLS = [
    "https://raw.githubusercontent.com/modood/Administrative-divisions-of-China/master/dist/pca-code.json",
    "https://fastly.jsdelivr.net/gh/modood/Administrative-divisions-of-China/dist/pca-code.json",
]

BLOCKED_M3U_KEYWORDS = (
    "更新时间", "更新時間", "维护时间", "維護時間", "维护内容", "維護内容", "维护內容",
    "公告说明", "公告說明", "公告", "说明", "說明", "支持作者", "支持打赏", "支持打賞",
    "免费订阅", "免費訂閲", "免費訂閱", "温馨提示", "溫馨提示", "建議使用", "建议使用",
    "请勿贩卖", "請勿販賣", "请勿频繁切换", "請勿頻繁切換", "个人觀看", "個人觀看", "刀刀影院"
)
BLOCKED_M3U_KEYWORDS_NORMALIZED = tuple(normalize_text_for_match(kw) for kw in BLOCKED_M3U_KEYWORDS)

CHANNEL_NAME_MARKERS = (
    "卫视", "衛視", "频道", "頻道", "台", "TV", "CCTV", "CGTN", "CHC",
    "影视", "影視", "电影", "電影", "新闻", "新聞", "综合", "綜合", "体育", "體育",
    "少儿", "少兒", "科教", "经济", "經濟", "生活", "都市", "公共", "纪实", "紀實",
    "卡通", "动画", "動漫", "戏曲", "戲曲", "文旅", "电视剧", "電視劇"
)

def resolve_province_aliases(province_name: str) -> Set[str]:
    aliases = {province_name}
    aliases.update(PROVINCE_ALIASES.get(province_name, set()))
    return aliases

def simplify_channel_name(channel_name: str) -> str:
    simplified = re.sub(r"[（(【\[][^\])）】]{0,24}[)）】\]]", "", channel_name)
    simplified = re.sub(r"\b(?:IPV6|HEVC|H\.?265|H\.?264|HDR|UHD|FHD|HD|SD|\d{3,4}P|4K|8K)\b", "", simplified, flags=re.IGNORECASE)
    return simplified.strip()

def strip_common_channel_suffixes(token: str) -> str:
    value = token
    value = re.sub(r"(?:TV|BTV|NBTV|CETV)\d+$", "", value)
    value = re.sub(r"[0-9一二三四五六七八九十]+套?$", "", value)
    value = re.sub(r"(?:IPV6|HEVC|H265|H264|HDR|UHD|FHD|HD|SD|4K|8K)$", "", value)
    changed = True
    while changed and value:
        changed = False
        for suffix in COMMON_CHANNEL_SUFFIXES_NORMALIZED:
            if value.endswith(suffix) and len(value) > len(suffix) + 1:
                value = value[:-len(suffix)]
                changed = True
                break
    return value

def extract_geo_tokens(channel_name: str, normalized_aliases: Set[str]) -> Set[str]:
    tokens = set()
    simplified = simplify_channel_name(channel_name)
    candidates = [simplified]
    candidates.extend(part for part in re.split(r"[|｜/\\\-_·•\s]+", simplified) if part)
    for candidate in candidates:
        normalized = normalize_text_for_match(candidate)
        if not normalized:
            continue
        trimmed = normalized
        for alias in sorted(normalized_aliases, key=len, reverse=True):
            if trimmed.startswith(alias) and len(trimmed) > len(alias) + 1:
                trimmed = trimmed[len(alias):]
                break
        trimmed = strip_common_channel_suffixes(trimmed).strip()
        if 2 <= len(trimmed) <= 8 and trimmed not in NON_GEO_TOKENS_NORMALIZED:
            tokens.add(trimmed)
    return tokens

def strip_suffix_once(name: str, suffixes: Iterable[str]) -> str:
    for suffix in sorted(suffixes, key=len, reverse=True):
        if name.endswith(suffix) and len(name) > len(suffix) + 1:
            return name[:-len(suffix)]
    return name

def normalize_province_name(name: str) -> str:
    return strip_suffix_once(re.sub(r"\s+", "", name), PROVINCE_SUFFIXES)

def geo_name_variants(name: str) -> Set[str]:
    cleaned = re.sub(r"\s+", "", name)
    if not cleaned:
        return set()
    variants = {cleaned}
    stripped = strip_suffix_once(cleaned, AREA_SUFFIXES)
    if stripped and stripped != cleaned:
        variants.add(stripped)
    return {v for v in variants if len(v) >= 2 and normalize_text_for_match(v) not in IGNORED_GEO_NAMES_NORMALIZED}

def iter_named_items(payload) -> Iterable[str]:
    if isinstance(payload, list):
        for item in payload:
            yield from iter_named_items(item)
    elif isinstance(payload, dict):
        name = payload.get("name")
        if isinstance(name, str) and name.strip():
            yield name.strip()
        has_known_children = False
        for key in ("children", "cities", "districts", "items", "list", "data"):
            child = payload.get(key)
            if child is not None:
                has_known_children = True
                yield from iter_named_items(child)
        if not has_known_children and "name" not in payload:
            for key, value in payload.items():
                if isinstance(key, str) and key.strip():
                    yield key.strip()
                if isinstance(value, (list, dict)):
                    yield from iter_named_items(value)

def build_province_lookup(province_channels: Dict[str, Set[str]]) -> Dict[str, str]:
    lookup = {}
    for province_key in province_channels:
        province_base = province_key.replace("频道", "")
        candidates = set(resolve_province_aliases(province_base))
        candidates.add(normalize_province_name(province_base))
        for candidate in candidates:
            normalized = normalize_text_for_match(normalize_province_name(candidate))
            if len(normalized) >= 2 and normalized not in lookup:
                lookup[normalized] = province_key
    return lookup

def collect_online_geo_tokens(geo_payload, province_channels: Dict[str, Set[str]]) -> Dict[str, Set[str]]:
    province_lookup = build_province_lookup(province_channels)
    added_tokens = defaultdict(set)
    if isinstance(geo_payload, list):
        province_nodes = geo_payload
    elif isinstance(geo_payload, dict):
        if isinstance(geo_payload.get("children"), list):
            province_nodes = geo_payload["children"]
        else:
            province_nodes = [{"name": key, "children": value} for key, value in geo_payload.items() if isinstance(value, (list, dict))]
    else:
        return added_tokens
    for node in province_nodes:
        if not isinstance(node, dict):
            continue
        province_name = node.get("name")
        if not isinstance(province_name, str) or not province_name.strip():
            continue
        province_normalized = normalize_text_for_match(normalize_province_name(province_name))
        province_key = province_lookup.get(province_normalized)
        if not province_key:
            for key, matched_province in province_lookup.items():
                if key and (key in province_normalized or province_normalized in key):
                    province_key = matched_province
                    break
        if not province_key:
            continue
        for raw_name in iter_named_items(node.get("children", [])):
            for variant in geo_name_variants(raw_name):
                normalized_variant = normalize_text_for_match(variant)
                if len(normalized_variant) >= 2 and normalized_variant not in IGNORED_GEO_NAMES_NORMALIZED:
                    added_tokens[province_key].add(variant)
    return added_tokens

async def load_online_geo_tokens(session: aiohttp.ClientSession, province_channels: Dict[str, Set[str]]) -> Dict[str, Set[str]]:
    for url in ONLINE_GEO_DATA_URLS:
        try:
            async with session.get(url, timeout=10) as response:
                if response.status != 200:
                    continue
                raw_text = await response.text(errors="ignore")
                payload = json.loads(raw_text)
                tokens = collect_online_geo_tokens(payload, province_channels)
                if tokens:
                    total = sum(len(items) for items in tokens.values())
                    print(f"Loaded {total} online geo tokens from: {url}")
                    return tokens
        except Exception:
            continue
    return {}

def build_province_matchers(province_channels: Dict[str, Set[str]]) -> Dict[str, List[str]]:
    province_matchers = {}
    for province, channels in province_channels.items():
        patterns = set()
        province_base = province.replace("频道", "")
        aliases = resolve_province_aliases(province_base)
        normalized_aliases = {normalize_text_for_match(alias) for alias in aliases}
        for ch in channels:
            normalized = normalize_text_for_match(ch)
            for geo_token in extract_geo_tokens(ch, normalized_aliases):
                patterns.add(geo_token)
        for alias in aliases:
            normalized_alias = normalize_text_for_match(alias)
            if len(normalized_alias) >= 2:
                patterns.add(normalized_alias)
        province_matchers[province] = sorted(patterns, key=len, reverse=True)
    return province_matchers

def match_province(normalized_channel: str, province_matchers: Dict[str, List[str]]) -> Optional[str]:
    best_match = None
    best_score = 0
    for province, patterns in province_matchers.items():
        for pattern in patterns:
            if pattern in normalized_channel:
                score = len(pattern)
                if score > best_score:
                    best_score = score
                    best_match = province
                break
    return best_match

# ==================== 频道名清洗 & 去重选优 ====================
def looks_like_notice_entry(channel: str, source_group_title: Optional[str] = None) -> bool:
    haystacks = [channel]
    if source_group_title:
        haystacks.append(source_group_title)
    for text in haystacks:
        raw_text = str(text or "").strip()
        if not raw_text:
            continue
        lowered = raw_text.casefold()
        if any(kw.casefold() in lowered for kw in BLOCKED_M3U_KEYWORDS):
            return True
        normalized = normalize_text_for_match(raw_text)
        if normalized and any(kw in normalized for kw in BLOCKED_M3U_KEYWORDS_NORMALIZED):
            return True
    return False

def _cleanup_extinf_payload(text: str) -> str:
    cleaned = str(text or "")
    cleaned = re.sub(r"https?://[^\s\"',]+", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"""(?ix)\b(?:tvg-id|tvg-name|tvg-logo|group-title|catchup|catchup-source|x-tvg-url)\s*=\s*(?:"[^"]*"|'[^']*'|[^\s,]+)""", " ", cleaned)
    cleaned = cleaned.replace("#EXTINF:-1", " ")
    cleaned = cleaned.replace(",", " ")
    cleaned = cleaned.replace('"', " ").replace("'", " ")
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()

def _extract_channel_candidates(text: str) -> List[str]:
    candidates = []
    raw_source = str(text or "")
    source = _cleanup_extinf_payload(raw_source)
    raw_without_urls = re.sub(r"https?://[^\s\"',]+", " ", raw_source, flags=re.IGNORECASE)
    if not raw_source and not source:
        return candidates
    patterns = [
        r"(?i)CCTV[\s-]?\d+\+?",
        r"(?i)(?:CGTN|CHC)[A-Z0-9+\-]*",
        r"[\u4e00-\u9fffA-Za-z0-9+]{1,24}(?:卫视|衛視|频道|頻道|影视|影視頻道|电影|電影|新闻|新聞|综合|綜合|体育|體育|少儿|少兒|科教|经济|經濟|生活|都市|公共|纪实|紀實|卡通|动画|動漫|戏曲|戲曲|文旅|电视台|電視台|电视|電視|台|TV)",
    ]
    for candidate_source in (raw_without_urls, source):
        if not candidate_source:
            continue
        for pattern in patterns:
            for match in re.findall(pattern, candidate_source):
                value = re.sub(r"\s+", "", match).strip("\"' ,")
                if value and len(value) <= 24:
                    candidates.append(value)
    token_source = _cleanup_extinf_payload(raw_without_urls)
    for token in re.split(r"[\s|/]+", token_source):
        token = token.strip("\"' ,")
        if 2 <= len(token) <= 16 and any(marker.lower() in token.lower() for marker in CHANNEL_NAME_MARKERS):
            candidates.append(token)
    return candidates

def sanitize_channel_name(channel: str, extinf_line: Optional[str] = None) -> str:
    raw_channel = str(channel or "").strip()
    if not raw_channel:
        return "Unknown"
    needs_repair = any(marker in raw_channel for marker in ("tvg-id=", "tvg-name=", "tvg-logo=", "group-title="))
    candidates = []
    if needs_repair:
        candidates.extend(_extract_channel_candidates(raw_channel))
        if extinf_line:
            candidates.extend(_extract_channel_candidates(extinf_line))
    if candidates:
        scored = Counter(candidates)
        best = sorted(scored.items(), key=lambda item: (-item[1], 0 if any(m.lower() in item[0].lower() for m in CHANNEL_NAME_MARKERS) else 1, len(item[0])))[0][0]
        return best
    cleaned = raw_channel.strip("\"' ,")
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned or "Unknown"

def parse_group_title_from_extinf(extinf_line: str) -> Optional[str]:
    patterns = [r'group-title\s*=\s*"([^"]+)"', r"group-title\s*=\s*'([^']+)'", r"group-title\s*=\s*([^,\s]+)"]
    for pattern in patterns:
        match = re.search(pattern, extinf_line, flags=re.IGNORECASE)
        if match:
            value = match.group(1).strip()
            if value:
                return value
    return None

def extract_urls_from_txt(content):
    urls = []
    for line in content.splitlines():
        line = line.strip()
        if line and ',' in line:
            channel, url = line.split(',', 1)
            channel = sanitize_channel_name(channel)
            if looks_like_notice_entry(channel):
                continue
            urls.append({"channel": channel, "url": url.strip(), "source_group_title": None})
    return urls

def extract_urls_from_m3u(content):
    urls = []
    lines = content.splitlines()
    channel = "Unknown"
    extinf_line = ""
    source_group_title = None
    for line in lines:
        line = line.strip()
        if line.startswith("#EXTINF:"):
            extinf_line = line
            parts = line.split(',', 1)
            raw_channel = parts[1] if len(parts) > 1 else "Unknown"
            channel = sanitize_channel_name(raw_channel, extinf_line)
            source_group_title = parse_group_title_from_extinf(line)
        elif line.startswith(('http://', 'https://')):
            if looks_like_notice_entry(channel, source_group_title):
                continue
            urls.append({"channel": channel.strip(), "url": line.strip(), "source_group_title": source_group_title})
    return urls

async def test_stream(session: aiohttp.ClientSession, semaphore: asyncio.Semaphore, url: str):
    async with semaphore:
        start = time.time()
        try:
            async with session.get(url, timeout=10) as resp:
                if resp.status == 200:
                    return True, time.time() - start
                return False, None
        except:
            return False, None

async def test_multiple_streams(session, semaphore, entries):
    tasks = [test_stream(session, semaphore, str(entry["url"]).strip()) for entry in entries]
    return await asyncio.gather(*tasks)

async def read_and_test_file(session, semaphore, file_path, is_m3u=False):
    try:
        async with session.get(file_path, timeout=15) as resp:
            if resp.status != 200:
                return []
            content = await resp.text(errors="ignore")
        if is_m3u:
            entries = extract_urls_from_m3u(content)
        else:
            entries = extract_urls_from_txt(content)
        # 初步去重（相同频道+URL）
        seen = set()
        unique_entries = []
        for e in entries:
            key = (normalize_text_for_match(e["channel"]), e["url"])
            if key not in seen:
                seen.add(key)
                unique_entries.append(e)
        results = await test_multiple_streams(session, semaphore, unique_entries)
        valid = []
        for (ok, lat), ent in zip(results, unique_entries):
            if ok:
                valid.append({"channel": ent["channel"], "url": ent["url"], "source_group_title": ent.get("source_group_title"), "latency": lat})
        return valid
    except:
        return []

def deduplicate_candidate_entries(entries):
    dedup = []
    seen = set()
    for e in entries:
        ch = sanitize_channel_name(str(e.get("channel", "")).strip())
        url = str(e.get("url", "")).strip()
        if not ch or not url.startswith(("http://", "https://")):
            continue
        if looks_like_notice_entry(ch, e.get("source_group_title")):
            continue
        key = (normalize_text_for_match(ch), url)
        if key in seen:
            continue
        seen.add(key)
        e["channel"] = ch
        e["url"] = url
        dedup.append(e)
    return dedup

def choose_better(current, candidate):
    cur_lat = current.get("latency")
    cand_lat = candidate.get("latency")
    cur_score = (cur_lat if isinstance(cur_lat, (int, float)) else float("inf"), 0 if str(current["url"]).startswith("https") else 1, len(str(current["url"])))
    cand_score = (cand_lat if isinstance(cand_lat, (int, float)) else float("inf"), 0 if str(candidate["url"]).startswith("https") else 1, len(str(candidate["url"])))
    return candidate if cand_score < cur_score else current

def select_best_streams(valid_entries):
    best = {}
    for e in valid_entries:
        ch = sanitize_channel_name(str(e.get("channel", "")).strip())
        url = str(e.get("url", "")).strip()
        if not ch or not url:
            continue
        key = normalize_text_for_match(ch)
        if key not in best:
            best[key] = e
        else:
            best[key] = choose_better(best[key], e)
    selected = list(best.values())
    selected.sort(key=lambda x: x.get("channel", ""))
    return selected

# ==================== 原代码中保留的配置与辅助函数 ====================
CONFIG = {
    "timeout": 10,
    "max_parallel": 30,
    "output_m3u": "Internet_iTV.m3u",
    "output_txt": "Internet_iTV.txt",
    "iptv_directory": "IPTV",
    "logo_base_url": "https://logo.jsdelivr.dpdns.org/tv"
}

def load_cctv_channels(file_path=".github/workflows/iTV/CCTV.txt"):
    cctv_channels = set()
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    cctv_channels.add(line)
    except FileNotFoundError:
        print(f"Error: {file_path} not found.")
    return cctv_channels

def load_province_channels(files):
    province_channels = defaultdict(set)
    for file_path in files:
        if not os.path.exists(file_path):
            print(f"Warning: {file_path} does not exist, skipping.")
            continue
        province_name = os.path.basename(file_path).replace(".txt", "")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        province_channels[province_name].add(line)
        except FileNotFoundError:
            print(f"Error: {file_path} not found.")
    return province_channels

def normalize_logo_name(channel_name):
    normalized = re.sub(r'[^\w\s]', '', channel_name)
    normalized = re.sub(r'\s+', '', normalized)
    normalized = re.sub(r'CCTV[-]?(\d+)(?:综合|新闻|财经|综艺|体育|电影|电视剧|戏曲|音乐|科教|少儿)?', r'CCTV\1', normalized)
    return normalized

def normalize_cctv_name(channel_name):
    return re.sub(r'CCTV[-]?(\d+)', r'CCTV\1', channel_name)

# ==================== 原代码的 generate_output_files（完全保留） ====================
def generate_output_files(valid_urls, cctv_channels, province_channels, m3u_filename, txt_filename):
    """生成排序后的 M3U 文件和 TXT 文件（TXT 按照分组结构输出）"""
    cctv_channels_list = []
    province_channels_list = defaultdict(list)
    satellite_channels = []
    
    # 构建四连字索引（优化匹配准确率）
    quadgram_to_province = defaultdict(set)

    # 获取动态关键词，用于过滤含时间名字的源
    filter_keywords = get_dynamic_keywords()

    # 遍历所有省份的所有频道，构建四连字索引
    for province, channels in province_channels.items():
        for channel_name in channels:
            # 添加原始词序的四连字
            if len(channel_name) >= 4:
                # 为频道名创建所有可能的四连字组合
                for i in range(len(channel_name) - 3):
                    quadgram = channel_name[i:i+4]
                    quadgram_to_province[quadgram].add(province)

    # 处理所有有效的URL，过滤含时间名字的源
    for channel, url, orig_logo in valid_urls:
        # 过滤包含日期或关键词的源
        if contains_date(channel) or any(keyword in channel for keyword in filter_keywords):
            continue  # 跳过含时间名字的源
        
        # 正规化频道名称，作为Logo文件名
        logo_name = normalize_logo_name(channel)
        
        # 生成Logo URL
        logo_url = f"{CONFIG['logo_base_url']}/{logo_name}.png"
        
        # 正规化 CCTV 频道名
        normalized_channel = normalize_cctv_name(channel)

        # 根据频道名判断属于哪个分组
        found_province = None
        
        # 1. 首先检查是否是CCTV频道
        if normalized_channel in cctv_channels:
            cctv_channels_list.append({
                "channel": channel,
                "url": url,
                "logo": logo_url,
                "group_title": "📺央视频道"
            })
        # 2. 检查是否是卫视频道
        elif "卫视" in channel:  # 卫视频道
            satellite_channels.append({
                "channel": channel,
                "url": url,
                "logo": logo_url,
                "group_title": "📡卫视频道"
            })
        # 3. 处理地方台频道
        else:
            # 优化中文四连字匹配
            province_scores = defaultdict(int)
            
            # 1. 精确匹配：检查频道名称是否完整包含在频道字符串中
            for province, channels in province_channels.items():
                for channel_name in channels:
                    if channel_name in channel:
                        found_province = province
                        break
                if found_province:
                    break
            
            # 2. 四连字匹配（使用更长的特征词提高准确性）
            if not found_province and len(channel) >= 4:
                # 为频道创建所有可能的四连字组合
                for i in range(len(channel) - 3):
                    quadgram = channel[i:i+4]
                    # 查找匹配的省份
                    if quadgram in quadgram_to_province:
                        for province in quadgram_to_province[quadgram]:
                            # 四连字匹配加更多权重
                            province_scores[province] += 2
            
            # 找到分数最高的省份
            if province_scores:
                max_score = max(province_scores.values())
                best_provinces = [p for p, s in province_scores.items() if s == max_score]
                # 如果有多个分数相同的省份，选择名称最短的（更具体）
                found_province = min(best_provinces, key=len) if best_provinces else None
            
            # 根据匹配结果分类频道
            if found_province:
                province_channels_list[found_province].append({
                    "channel": channel,
                    "url": url,
                    "logo": logo_url,
                    "group_title": f"{found_province}"
                })
            else:
                # 归入默认分组
                province_channels_list["🧯樂玩公社"].append({
                    "channel": channel,
                    "url": url,
                    "logo": logo_url,
                    "group_title": "🧯樂玩公社"
                })

    # --- URL去重逻辑开始 ---
    # 按分组优先级排序 (CCTV -> 卫视 -> 省份 -> 樂玩公社)
    all_groups = [
        ("📺央视频道", cctv_channels_list),
        ("📡卫视频道", satellite_channels)
    ]
    
    # 添加省份频道（按省份名称排序）
    for province in sorted(province_channels_list.keys()):
        if province == "🧯樂玩公社":
            continue
        all_groups.append((province, province_channels_list[province]))
    
    # 添加樂玩公社分组
    all_groups.append(("🧯樂玩公社", province_channels_list.get("🧯樂玩公社", [])))

    # 使用字典根据URL去重（保留每个URL第一次出现的频道）
    seen_urls = set()
    deduped_channels = []
    
    for group_title, channels in all_groups:
        if not channels: continue
        channels.sort(key=lambda x: x["channel"])
        for channel_info in channels:
            url = channel_info["url"]
            if url not in seen_urls:
                seen_urls.add(url)
                deduped_channels.append({
                    "channel": channel_info["channel"],
                    "url": url,
                    "logo": channel_info["logo"],
                    "group_title": group_title
                })

    # 确保输出目录存在
    os.makedirs(os.path.dirname(m3u_filename) or '.', exist_ok=True)
    os.makedirs(os.path.dirname(txt_filename) or '.', exist_ok=True)

    # 写入 M3U 文件
    with open(m3u_filename, 'w', encoding='utf-8') as f:
        f.write("#EXTM3U x-tvg-url=\"https://itv.sspai.pp.ua/epg.xml.gz\" catchup=\"append\" catchup-source=\"?playseek=${(b)yyyyMMddHHmmss}-${(e)yyyyMMddHHmmss}\"\n")
        f.write("#EXTINF:-1 tvg-id=\"温馨提示\" tvg-name=\"温馨提示\" tvg-logo=\"https://logo.jsdelivr.dpdns.org/tv/温馨提示.png\" group-title=\"🦧温馨提示\",温馨提示\n")
        f.write("https://icloud.ifanr.pp.ua/温馨提示.mp4\n")
        f.write("#EXTINF:-1 tvg-id=\"谨防诈骗\" tvg-name=\"谨防诈骗\" tvg-logo=\"https://logo.jsdelivr.dpdns.org/tv/谨防诈骗.png\" group-title=\"🦧温馨提示\",谨防诈骗\n")
        f.write("https://icloud.ifanr.pp.ua/温馨提示.mp4\n")
        f.write("#EXTINF:-1 tvg-id=\"禁止蕉绿\" tvg-name=\"禁止蕉绿\" tvg-logo=\"https://logo.jsdelivr.dpdns.org/tv/禁止蕉绿.png\" group-title=\"🦧温馨提示\",禁止蕉绿\n")
        f.write("https://icloud.ifanr.pp.ua/温馨提示.mp4\n")
        f.write("#EXTINF:-1 tvg-id=\"Cloudflare TV\" tvg-name=\"Cloudflare TV\" tvg-logo=\"https://logo.jsdelivr.dpdns.org/tv/CloudflareTV.png\" group-title=\"🦧温馨提示\",Cloudflare TV\n")
        f.write("https://cloudflare.tv/hls/live.m3u8\n")
        
        for channel_info in deduped_channels:
            channel_id = channel_info['channel'].replace('-', '')
            f.write(f"#EXTINF:-1 tvg-name=\"{channel_id}\" tvg-logo=\"{channel_info['logo']}\" group-title=\"{channel_info['group_title']}\",{channel_info['channel']}\n")
            f.write(f"{channel_info['url']}\n")
            
    print(f"🎉 Generated M3U file: {m3u_filename}")
    print(f"文件位置: {os.path.abspath(m3u_filename)}")
    print(f"文件大小: {os.path.getsize(m3u_filename)} 字节")
    
    # 写入结构化的 TXT 文件 (按分组结构输出)
    with open(txt_filename, 'w', encoding='utf-8') as f:
        grouped_channels = defaultdict(list)
        for channel_info in deduped_channels:
            grouped_channels[channel_info['group_title']].append(channel_info)
        
        group_order = [
            "📛4K·8K频道", "📺央视频道", "📡卫视频道", "💰付费频道", "🍁数字频道",
            "🍱NewTV频道", "🐳iHOT频道", "🦜DOX频道", "🐌CIBN频道", "💾IPTV频道",
            "🦥教育频道", "🚃重庆频道", "🚄四川频道", "🚅云南频道", "🚈安徽频道",
            "🚝福建频道", "🚋甘肃频道", "🚌广东频道", "🚎广西频道", "🚐贵州频道",
            "🚑海南频道", "🚒河北频道", "🚓河南频道", "🚕黑龙江频道", "🚗湖北频道",
            "🚙湖南频道", "🚚吉林频道", "🚂江苏频道", "🚛江西频道", "🚜辽宁频道",
            "🏎️内蒙古频道", "🏍️宁夏频道", "🛵青海频道", "🦽山东频道", "🦼山西频道",
            "🛺陕西频道", "🚲上海频道", "🛴天津频道", "🛹新疆频道", "🚞浙江频道",
            "🛩️北京频道", "🏍️港澳台频道", "🚸少儿频道", "🎥咪咕视频", "🎬影视剧频道",
            "🎮游戏频道", "🎵音乐频道", "🏀体育频道", "🏛经典剧场", "🪁动漫频道",
            "🐼熊猫频道", "🗺️直播中国", "🦙解说频道", "🏮历年春晚", "🧯樂玩公社"
        ]
        
        for group in group_order:
            if group in grouped_channels and grouped_channels[group]:
                f.write(f"{group},#genre#\n")
                channels = sorted(grouped_channels[group], key=lambda x: x['channel'])
                for ch in channels:
                    f.write(f"{ch['channel']},{ch['url']}\n")
        
        for group, channels in grouped_channels.items():
            if group not in group_order and channels:
                f.write(f"{group},#genre#\n")
                channels = sorted(channels, key=lambda x: x['channel'])
                for ch in channels:
                    f.write(f"{ch['channel']},{ch['url']}\n")
                    
    print(f"🎉 Generated structured TXT file: {txt_filename}")
    print(f"文件位置: {os.path.abspath(txt_filename)}")
    print(f"文件大小: {os.path.getsize(txt_filename)} 字节")

# ==================== 主函数（融合增强功能） ====================
async def main(file_urls, cctv_channel_file, province_channel_files):
    # 加载 CCTV 和省份频道列表（原样）
    cctv_channels = load_cctv_channels(cctv_channel_file)
    province_channels = load_province_channels(province_channel_files)

    # 在线地理数据增强省份匹配词（可选）
    connector = aiohttp.TCPConnector(limit=CONFIG["max_parallel"]*2)
    timeout = aiohttp.ClientTimeout(total=CONFIG["timeout"])
    async with aiohttp.ClientSession(cookie_jar=None, timeout=timeout, connector=connector) as session:
        online_tokens = await load_online_geo_tokens(session, province_channels)
        if online_tokens:
            for prov, tokens in online_tokens.items():
                province_channels[prov].update(tokens)
            print("Online geo tokens merged into province channels.")
        else:
            print("No online geo tokens loaded, using only local files.")

        sem = asyncio.Semaphore(CONFIG["max_parallel"])
        tasks = []
        for url in file_urls:
            if url.endswith(('.m3u', '.m3u8')):
                tasks.append(read_and_test_file(session, sem, url, is_m3u=True))
            elif url.endswith('.txt'):
                tasks.append(read_and_test_file(session, sem, url, is_m3u=False))
        results = await asyncio.gather(*tasks)
    
    all_entries = []
    for res in results:
        all_entries.extend(res)
    
    # 去重 & 选优
    deduped = deduplicate_candidate_entries(all_entries)
    best_entries = select_best_streams(deduped)
    print(f"Total valid streams: {len(all_entries)}, deduplicated: {len(deduped)}, best-per-channel: {len(best_entries)}")
    
    # 转换成 generate_output_files 需要的格式：列表 of (channel, url, orig_logo)
    valid_urls = [(entry["channel"], entry["url"], None) for entry in best_entries]
    
    # 调用原代码的输出函数（完全保留原有分组逻辑）
    generate_output_files(valid_urls, cctv_channels, province_channels, CONFIG["output_m3u"], CONFIG["output_txt"])

if __name__ == "__main__":
    file_urls = [
        "https://raw.githubusercontent.com/mytv-android/iptv-api/master/output/result.m3u",
        "https://raw.githubusercontent.com/vbskycn/iptv/master/tv/iptv4.m3u"
    ]
    cctv_channel_file = ".github/workflows/iTV/CCTV.txt"
    province_channel_files = [
        ".github/workflows/iTV/📛4K·8K频道.txt",
        ".github/workflows/iTV/💰付费频道.txt",
        ".github/workflows/iTV/🍁数字频道.txt",
        ".github/workflows/iTV/🍱NewTV频道.txt",
        ".github/workflows/iTV/🐳iHOT频道.txt",
        ".github/workflows/iTV/🦜DOX频道.txt",
        ".github/workflows/iTV/🐌CIBN频道.txt",
        ".github/workflows/iTV/💾IPTV频道.txt",
        ".github/workflows/iTV/🦥教育频道.txt",
        ".github/workflows/iTV/📡卫视频道.txt",
        ".github/workflows/iTV/🚃重庆频道.txt",
        ".github/workflows/iTV/🚄四川频道.txt",
        ".github/workflows/iTV/🚅云南频道.txt",
        ".github/workflows/iTV/🚈安徽频道.txt",
        ".github/workflows/iTV/🚝福建频道.txt",
        ".github/workflows/iTV/🚋甘肃频道.txt",
        ".github/workflows/iTV/🚌广东频道.txt",
        ".github/workflows/iTV/🚎广西频道.txt",
        ".github/workflows/iTV/🚐贵州频道.txt",
        ".github/workflows/iTV/🚑海南频道.txt",
        ".github/workflows/iTV/🚒河北频道.txt",
        ".github/workflows/iTV/🚓河南频道.txt",
        ".github/workflows/iTV/🚕黑龙江频道.txt",
        ".github/workflows/iTV/🚗湖北频道.txt",
        ".github/workflows/iTV/🚙湖南频道.txt",
        ".github/workflows/iTV/🚚吉林频道.txt",
        ".github/workflows/iTV/🚂江苏频道.txt",
        ".github/workflows/iTV/🚛江西频道.txt",
        ".github/workflows/iTV/🚜辽宁频道.txt",
        ".github/workflows/iTV/🏎️内蒙古频道.txt",
        ".github/workflows/iTV/🏍️宁夏频道.txt",
        ".github/workflows/iTV/🛵青海频道.txt",
        ".github/workflows/iTV/🦽山东频道.txt",
        ".github/workflows/iTV/🦼山西频道.txt",
        ".github/workflows/iTV/🛺陕西频道.txt",
        ".github/workflows/iTV/🚲上海频道.txt",
        ".github/workflows/iTV/🛴天津频道.txt",
        ".github/workflows/iTV/🛹新疆频道.txt",
        ".github/workflows/iTV/🚞浙江频道.txt",
        ".github/workflows/iTV/🛩️北京频道.txt",
        ".github/workflows/iTV/🏍️港澳台频道.txt",
        ".github/workflows/iTV/🚸少儿频道.txt",
        ".github/workflows/iTV/🎥咪咕视频.txt",
        ".github/workflows/iTV/🎬影视剧频道.txt",
        ".github/workflows/iTV/🎮游戏频道.txt",
        ".github/workflows/iTV/🎵音乐频道.txt",
        ".github/workflows/iTV/🏀体育频道.txt",
        ".github/workflows/iTV/🏛经典剧场.txt",
        ".github/workflows/iTV/🪁动漫频道.txt",
        ".github/workflows/iTV/🐼熊猫频道.txt",
        ".github/workflows/iTV/🗺️直播中国.txt",
        ".github/workflows/iTV/🦙解说频道.txt",
        ".github/workflows/iTV/🏮历年春晚.txt"
    ]
    asyncio.run(main(file_urls, cctv_channel_file, province_channel_files))
