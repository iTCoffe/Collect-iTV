import os
import aiohttp
import asyncio
import re
from collections import defaultdict
from datetime import datetime, timedelta

# 配置
CONFIG = {
    "timeout": 20,
    "max_parallel": 10,
    "output_m3u": "BiTV.m3u",
    "output_txt": "BiTV.txt",
    "logo_base_url": "https://logo.jsdelivr.dpdns.org/tv",
    "source_url": "https://zubotv.ugreen.workers.dev",
    "itv_dir": ".github/workflows/iTV"
}

def get_dynamic_keywords():
    """动态生成过滤词"""
    today = datetime.now().strftime("%Y-%m-%d")
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    return ["免费提供", "独家", "最新", "稳定", today, tomorrow]

def contains_date(text):
    """正则匹配日期"""
    return re.search(r"\d{4}-\d{2}-\d{2}", text) is not None

def normalize_logo_name(channel_name):
    """标准化名称以匹配图标库文件名"""
    # 替换特定的CCTV格式，例如 CCTV-1综合 -> CCTV1
    normalized = re.sub(r'CCTV[-]?(\d+).*', r'CCTV\1', channel_name)
    # 进一步移除所有非中英文字符
    normalized = re.sub(r'[^\w\u4e00-\u9fa5]', '', normalized)
    return normalized

def load_local_categories():
    """读取本地 iTV 文件夹下的分类参考"""
    cctv_channels = set()
    province_channels = defaultdict(set)
    
    if not os.path.exists(CONFIG["itv_dir"]):
        print(f"Warning: Directory {CONFIG['itv_dir']} not found.")
        return cctv_channels, province_channels

    for filename in os.listdir(CONFIG["itv_dir"]):
        if not filename.endswith(".txt"): continue
        file_path = os.path.join(CONFIG["itv_dir"], filename)
        category_name = filename.replace(".txt", "")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                name = line.strip()
                if not name: continue
                if category_name == "CCTV":
                    cctv_channels.add(name)
                else:
                    province_channels[category_name].add(name)
    return cctv_channels, province_channels

async def fetch_remote_source():
    """带 Header 抓取源文件"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    connector = aiohttp.TCPConnector(ssl=False)
    try:
        async with aiohttp.ClientSession(connector=connector, headers=headers) as session:
            async with session.get(CONFIG["source_url"], timeout=CONFIG["timeout"]) as response:
                if response.status == 200:
                    text = await response.text()
                    # 简单解析 TXT 格式为 (频道名, URL)
                    results = []
                    for line in text.splitlines():
                        if "," in line and not line.startswith("#"):
                            parts = line.split(',', 1)
                            results.append((parts[0].strip(), parts[1].strip()))
                    return results
                return []
    except Exception as e:
        print(f"Fetch Error: {e}")
        return []

def generate_files(valid_urls, cctv_channels, province_channels):
    """处理分组排序并写入文件"""
    filter_keywords = get_dynamic_keywords()
    final_groups = defaultdict(list)
    seen_urls = set()

    # 构建四连字索引 (核心算法)
    quadgram_to_province = defaultdict(set)
    for prov, channels in province_channels.items():
        for ch in channels:
            if len(ch) >= 4:
                for i in range(len(ch) - 3):
                    quadgram_to_province[ch[i:i+4]].add(prov)

    for name, url in valid_urls:
        # 基础过滤
        if url in seen_urls or contains_date(name) or any(k in name for k in filter_keywords):
            continue
        
        seen_urls.add(url)
        logo_name = normalize_logo_name(name)
        logo_url = f"{CONFIG['logo_base_url']}/{logo_name}.png"
        
        # 匹配逻辑
        group = "🧯樂玩公社"
        # 1. CCTV 匹配 (支持 CCTV1 和 CCTV-1 互转匹配)
        norm_name = re.sub(r'CCTV[-]?(\d+)', r'CCTV\1', name)
        if name in cctv_channels or norm_name in cctv_channels:
            group = "📺央视频道"
        # 2. 卫视匹配
        elif "卫视" in name:
            group = "📡卫视频道"
        # 3. 地方台四连字匹配
        else:
            province_scores = defaultdict(int)
            for i in range(len(name) - 3):
                q = name[i:i+4]
                if q in quadgram_to_province:
                    for p in quadgram_to_province[q]: province_scores[p] += 1
            if province_scores:
                group = max(province_scores, key=province_scores.get)

        final_groups[group].append({"name": name, "url": url, "logo": logo_url})

    # --- 写入文件 ---
    with open(CONFIG["output_m3u"], "w", encoding="utf-8") as m, \
         open(CONFIG["output_txt"], "w", encoding="utf-8") as t:
        
        # M3U 头部
        m.write('#EXTM3U x-tvg-url="https://itv.sspai.indevs.in/epg.xml.gz" catchup="append" catchup-source="?playseek=${(b)yyyyMMddHHmmss}-${(e)yyyyMMddHHmmss}"\n')
        
        # 写入固定提示
        tips = ["温馨提示", "禁止蕉绿", "Cloudflare TV"]
        for tip in tips:
            m.write(f'#EXTINF:-1 tvg-id="{tip}" tvg-name="{tip}" tvg-logo="{CONFIG["logo_base_url"]}/{tip}.png" group-title="🦧温馨提示",{tip}\nhttps://icloud.ifanr.pp.ua/温馨提示.mp4\n')

        # 排序分组并写入 (CCTV 和 卫视 优先)
        priority = ["📺央视频道", "📡卫视频道"]
        sorted_groups = priority + sorted([g for g in final_groups.keys() if g not in priority])

        for g_name in sorted_groups:
            channels = final_groups.get(g_name, [])
            if not channels: continue
            
            t.write(f"{g_name},#genre#\n")
            for ch in sorted(channels, key=lambda x: x['name']):
                # M3U 格式
                m.write(f'#EXTINF:-1 tvg-id="{ch["name"]}" tvg-name="{ch["name"]}" tvg-logo="{ch["logo"]}" group-title="{g_name}",{ch["name"]}\n{ch["url"]}\n')
                # TXT 格式
                t.write(f"{ch['name']},{ch['url']}\n")

async def main():
    print("🚀 Starting Update...")
    entries = await fetch_remote_source()
    if not entries:
        print("❌ Error: No source data fetched.")
        return
    
    cctv, provinces = load_local_categories()
    generate_files(entries, cctv, provinces)
    print(f"✨ Successfully updated! M3U and TXT generated.")

if __name__ == "__main__":
    asyncio.run(main())
