import os
import aiohttp
import asyncio
import time
from collections import defaultdict
import re
from datetime import datetime, timedelta


def get_dynamic_keywords():
    """
    动态生成需要过滤的关键词（今天的日期、明天的日期以及固定关键词）
    """
    # 获取今天和明天的日期
    today = datetime.now().strftime("%Y-%m-%d")
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    
    fixed_keywords = ["免费提供", today, tomorrow]
    return fixed_keywords

def contains_date(text):
    """
    检测字符串中是否包含日期格式（如 YYYY-MM-DD）
    """
    date_pattern = r"\d{4}-\d{2}-\d{2}"  # 正则表达式匹配 YYYY-MM-DD
    return re.search(date_pattern, text) is not None


# 配置
CONFIG = {
    "timeout": 10,  # Timeout in seconds
    "max_parallel": 30,  # Max concurrent requests
    "output_file": "Internet_iTV.m3u",  # Output file for the sorted M3U
    "iptv_directory": "IPTV"  # Directory containing IPTV files
}


# 读取 CCTV 频道列表
def load_cctv_channels(file_path=".github/workflows/iTV/CCTV.txt"):
    """从文件加载 CCTV 频道列表"""
    cctv_channels = set()
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            for line in file:
                line = line.strip()
                if line:  # Ignore empty lines
                    cctv_channels.add(line)
    except FileNotFoundError:
        print(f"Error: The file {file_path} was not found.")
    return cctv_channels


# 读取 IPTV 目录下所有省份频道文件
def load_province_channels(files):
    """加载多个省份的频道列表"""
    province_channels = defaultdict(set)

    for file_path in files:
        province_name = os.path.basename(file_path).replace(".txt", "")  # 使用文件名作为省份名称

        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                for line in file:
                    line = line.strip()
                    if line:  # 忽略空行
                        province_channels[province_name].add(line)
        except FileNotFoundError:
            print(f"Error: The file {file_path} was not found.")

    return province_channels


# 正规化 CCTV 频道名称
def normalize_cctv_name(channel_name):
    """将 CCTV 频道名称进行正规化，例如 CCTV-1 -> CCTV1"""
    return re.sub(r'CCTV[-]?(\d+)', r'CCTV\1', channel_name)


# 从 TXT 文件中提取 IPTV 链接
def extract_urls_from_txt(content):
    """从 TXT 文件中提取 IPTV 链接"""
    urls = []
    for line in content.splitlines():
        line = line.strip()
        if line and ',' in line:  # 格式应该是: <频道名>,<URL>
            parts = line.split(',', 1)
            urls.append((parts[0], parts[1], None))  # 提取频道名、URL和logo (TXT没有logo)
    return urls


# 从 M3U 文件中提取 IPTV 链接
def extract_urls_from_m3u(content):
    """从 M3U 文件中提取 IPTV 链接及原始logo"""
    urls = []
    lines = content.splitlines()
    current_channel = "Unknown"
    current_logo = None  # 存储当前频道的原始logo

    for line in lines:
        line = line.strip()
        if line.startswith("#EXTINF:"):
            # 解析频道信息
            current_logo = None  # 重置logo
            # 尝试提取tvg-logo属性
            match = re.search(r'tvg-logo="([^"]+)"', line)
            if match:
                current_logo = match.group(1)
                
            # 提取频道名称（逗号后的部分）
            parts = line.split(',', 1)
            current_channel = parts[1] if len(parts) > 1 else "Unknown"
            
        elif line.startswith(('http://', 'https://')):
            # 存储频道名、URL和原始logo（如果存在）
            urls.append((current_channel, line, current_logo))
            current_logo = None  # 重置当前logo
    return urls


# 测试多个 IPTV 链接的可用性和速度（可选）
async def test_multiple_streams(urls):
    """测试多个 IPTV 链接（可选）"""
    return [(True, 0.0)] * len(urls)  # 总是返回所有链接都有效


# 读取文件并提取 URL（支持 M3U 或 TXT 格式）
async def read_and_test_file(file_path, is_m3u=False):
    """读取文件并提取所有 URL（不过滤）"""
    try:
        # 获取文件内容
        async with aiohttp.ClientSession(cookie_jar=None) as session:  # 禁用 cookie 处理
            async with session.get(file_path) as response:
                content = await response.text()

        # 提取 URL
        if is_m3u:
            entries = extract_urls_from_m极(con极ent)
        else:
            entries = extract_urls_from_txt(content)

        # 直接返回所有 URL（不过滤）
        return entries

    except Exception as e:
        return []


# 生成排序后的 M3U 文件
def generate_sorted_m3u(valid_urls, cctv_channels, province_channels, filename):
    """生成排序后的 M3U 文件，仅对URL去重，保留相同频道的不同源"""
    # 使用字典来去重（仅基于URL）
    seen_urls = set()  # 用于记录已处理的URL
    unique_channels = []  # 存储去重后的频道
    
    # 获取动态关键词，用于过滤含时间名字的源
    filter_keywords = get_dynamic_keywords()

    # 第一步：过滤并去重所有频道条目
    for channel, url, orig_logo in valid_urls:
        # 跳过空频道名或URL
        if not channel or not url:
            continue
            
        # 过滤包含日期或关键词的源
        if contains_date(channel) or any(keyword in channel for keyword in filter_keywords):
            continue  
        
        # 检查URL是否已处理过（去重）
        if url in seen_urls:
            continue
            
        # 加入已处理集合
        seen_urls.add(url)
        
        # 添加到去重后的列表
        unique_channels.append((channel, url, orig_logo))
    
    # 初始化分组列表
    cctv_channels_list = []
    province_channels_list = defaultdict(list)
    satellite_channels = []
    other_channels = []
    
    # 创建频道名到省份的映射表
    channel_to_province = {}
    for province, channels in province_channels.items():
        for channel_name in channels:
            # 频道名作为key，省份作为value
            channel_to_province[channel_name] = province

    # 第二步：分类处理去重后的频道
    for channel, url, orig_logo in unique_channels:
        # 正规化 CCTV 频道名
        normalized_channel = normalize_cctv_name(channel)

        # 根据频道名判断属于哪个分组
        found_province = None
        
        # 1. 首先检查是否是CCTV频道
        if normalized_channel in cctv_channels:
            cctv_channels_list.append({
                "channel": channel,
                "url": url,
                "logo": orig_logo,
                "group_title": "📺央视频道"
            })
        # 2. 检查是否是卫视频道
        elif "卫视" in channel:
            satellite_channels.append({
                "channel": channel,
                "url极": url,
                "logo": orig_logo,
                "group_title": "📡卫视频道"
            })
        # 3. 处理地方台频道 - 使用精确匹配
        else:
            # 检查频道是否在省份频道列表中（精确匹配）
            if channel in channel_to_province:
                found_province = channel_to_province[channel]
            else:
                # 检查是否包含省份频道名称（部分匹配）
                for known_channel, province in channel_to_province.items():
                    if known_channel in channel:
                        found_province = province
                        break
            
            # 根据匹配结果分类频道
            if found_province:
                province_channels_list[found_province].append({
                    "channel": channel,
                    "url": url,
                    "logo": orig_logo,
                    "group_title": f"{found_province}"
                })
            else:
                # 包含"台"字的频道归入其他频道
                if "台" in channel:
                    province_channels_list["🧮其他频道"].append({
                        "channel": channel,
                        "url": url,
                        "logo": orig_logo,
                        "group_title": "🧮其他频道"
                    })
                else:
                    other_channels.append({
                        "channel": channel,
                        "url": url,
                        "logo": orig_logo,
                        "group_title": "🧮其他频道"
                    })

    # 第三步：分组内排序（不再去重）
    for province in province_channels_list:
        # 排序但不移除相同频道名称的条目（因为URL不同）
        province_channels_list[province].sort(key=lambda x: x["channel"])

    # 其他分组排序
    cctv_channels_list.sort(key=lambda x: x["channel"])
    satellite_channels.sort(key=lambda x: x["channel"])
    other_channels.sort(key=lambda x: x["channel"])

    # 合并所有频道
    all_channels = (
        cctv_channels_list +
        satellite_channels +
        [channel for province in sorted(province_channels_list) 
         for channel in province_channels_list[province]] +
        other_channels
    )

    # 写入 M3U 文件
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("#EXTM3U x-tvg-url=\"https://112114.shrimp.cloudns.biz/epg.xml\" catchup=\"append\" catchup-source=\"?playseek=${(b)yyyyMMddHHmmss}-${(e)yyyyMMddHHmmss}\"\n")
        
        for channel_info in all_channels:
            # 处理特殊字符，确保频道名称不会干扰M3U格式
            channel_name = channel_info['channel'].replace(',', '，')  # 替换可能破坏格式的逗号
            channel_id = channel_name.replace('-', '')
            
            # 处理空logo的情况
            logo_url = channel_info['logo'] if channel_info['logo'] else ""
            f.write(
                f"#EXTINF:-1 tvg-name=\"{channel_id}\" tvg-logo=\"{logo_url}\" group-title=\"{channel_info['group_title']}\",{channel_name}\n")
            f.write(f"{channel_info['url']}\n")
            
        # 添加文件末尾的备注信息
        f.write(f"\n# 频道总数: {len(all_channels)}\n")
        f.write(f"# 唯一URL数: {len(seen_urls)}\n")
        f.write(f"# 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"# 源列表: {', '.join([os.path.basename(f) for f in file_urls])}")

# 主函数：处理多个文件并生成 M3U 输出
async def main(file_urls, cctv_channel_file, province_channel_files):
    """主函数处理多个文件"""
    # 加载 CCTV 频道列表
    cctv_channels = load_cctv_channels(cctv_channel_file)

    # 加载多个省份频道列表
    province_channels = load_province_channels(province_channel_files)

    all_valid_urls = []

    semaphore = asyncio.Semaphore(CONFIG["max_parallel"])

    async def limited_task(task):
        async with semaphore:
            return await task

    tasks = []
    for file_url in file_urls:
        if file_url.endswith(('.m3u', '.m3u8')):
            tasks.append(limited_task(read_and_test_file(file_url, is_m3u=True)))
        elif file_url.endswith('.txt'):
            tasks.append(limited_task(read_and_test_file(file_url, is_m3u=False)))
        else:
            continue

    results = await asyncio.gather(*tasks)
    for valid_urls in results:
        all_valid_urls.extend(valid_urls)

    # 生成排序后的 M3U 文件
    generate_sorted_m3u(all_valid_urls, cctv_channels, province_channels, CONFIG["output_file"])
    print(f"🎉 Generated sorted M3U file: {CONFIG['output_file']}")
    print(f"📺 Total channels: {len(all_valid_urls)}")
    print(f"✅ Unique URLs: {len(set([url for _, url, _ in all_valid_urls]))}")


if __name__ == "__main__":
    # IPTV 文件 URL（您可以添加自己的文件 URL 列表）
    file_urls = [
        "https://raw.githubusercontent.com/mytv-android/iptv-api/master/output/result.m3u",
        "https://raw.githubusercontent.com/vbskycn/iptv/master/tv/iptv4.m3u",
        "https://raw.githubusercontent.com/kilvn/iptv/master/iptv.m3u"
    ]

    # CCTV 频道文件（例如 IPTV/CCTV.txt）
    cctv_channel_file = ".github/workflows/iTV/CCTV.txt"

    # 省份频道文件列表
    province_channel_files = [
        ".github/workflows/iTV/💰央视付费频道.txt",
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
        ".github/workflows/i极TV/🚑海南频道.txt",
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
        ".github/workflows/iTV/🎥咪咕视频.txt",
        ".github/workflows/iTV/🎬影视剧频道.txt",
        ".github/workflows/iTV/🎮游戏频道.txt",
        ".github/workflows/iTV/🎵音乐频道.txt",
        ".github/workflows/iTV/🏀体育频道.txt",
        ".github/workflows/iTV/🏛经典剧场.txt",
        ".github/workflows/iTV/🚁直播中国.txt",
        ".github/workflows/iTV/🏮历年春晚.txt",
        ".github/workflows/iTV/🪁动漫频道.txt"
    ]

    # 执行主函数
    asyncio.run(main(file_urls, cctv_channel_file, province_channel_files))
