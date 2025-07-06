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
    "output_m3u": "Internet_iTV.m3u",  # Output file for the sorted M3U
    "output_txt": "Internet_iTV.txt",  # Output file for the TXT format
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
            entries = extract_urls_from_m3u(content)
        else:
            entries = extract_urls_from_txt(content)

        # 直接返回所有 URL（不过滤）
        return entries

    except Exception as e:
        return []


# 生成排序后的 M3U 文件和 TXT 文件
def generate_output_files(valid_urls, cctv_channels, province_channels, m3u_filename, txt_filename):
    """生成排序后的 M3U 文件和 TXT 文件（TXT 按照分组结构输出）"""
    # 分类容器
    cctv_channels_list = []              # 1. 央视频道
    cctv_pay_channels_list = []          # 2. 央视付费频道
    satellite_channels = []              # 3. 卫视频道
    province_channels_dict = {}          # 4. 地方频道（按省份存储）
    other_categories_dict = defaultdict(list)  # 5. 其他类别（咪咕、动漫等）
    other_channels = []                  # 6. 其他频道
    
    # 构建四连字索引（优化匹配准确率）
    quadgram_to_province = defaultdict(set)
    # 获取动态关键词，用于过滤含时间名字的源
    filter_keywords = get_dynamic_keywords()
    
    # 预定义其他类别关键词映射
    other_categories = {
        "🚸少儿频道": ["少儿"],
        "🎥咪咕视频": ["咪咕"],
        "🎬影视剧频道": ["影视", "剧场", "影视剧"],
        "🎮游戏频道": ["游戏"],
        "🎵音乐频道": ["音乐"],
        "🏀体育频道": ["体育"],
        "🏛经典剧场": ["经典剧场"],
        "🚁直播中国": ["直播中国"],
        "🪁动漫频道": ["动漫", "卡通"]
    }
    
    # 定义地方省份顺序
    province_order = [
        "🚃重庆频道", "🚄四川频道", "🚅云南频道", "🚈安徽频道", "🚝福建频道", 
        "🚋甘肃频道", "🚌广东频道", "🚎广西频道", "🚐贵州频道", "🚑海南频道", 
        "🚒河北频道", "🚓河南频道", "🚕黑龙江频道", "🚗湖北频道", "🚙湖南频道", 
        "🚚吉林频道", "🚂江苏频道", "🚛江西频道", "🚜辽宁频道", "🏎️内蒙古频道", 
        "🏍️宁夏频道", "🛵青海频道", "🦽山东频道", "🦼山西频道", "🛺陕西频道", 
        "🚲上海频道", "🛴天津频道", "🛹新疆频道", "🚞浙江频道", "🛩️北京频道", 
        "🏍️港澳台频道"
    ]
    
    # 构建四连字索引
    for province, channels in province_channels.items():
        for channel_name in channels:
            if len(channel_name) >= 4:
                for i in range(len(channel_name) - 3):
                    quadgram = channel_name[i:i+4]
                    quadgram_to_province[quadgram].add(province)
    
    # 处理所有有效的URL，过滤含时间名字的源
    for channel, url, orig_logo in valid_urls:
        # 过滤包含日期或关键词的源
        if contains_date(channel) or any(keyword in channel for keyword in filter_keywords):
            continue
        
        # 正规化 CCTV 频道名
        normalized_channel = normalize_cctv_name(channel)
        
        # 1. 检查是否是CCTV频道（包括付费）
        if normalized_channel in cctv_channels:
            if "付费" in channel:
                cctv_pay_channels_list.append({
                    "channel": channel,
                    "url": url,
                    "logo": orig_logo,
                    "group_title": "💰央视付费频道"
                })
            else:
                cctv_channels_list.append({
                    "channel": channel,
                    "url": url,
                    "logo": orig_logo,
                    "group_title": "📺央视频道"
                })
            continue
                
        # 3. 检查是否是卫视频道
        if "卫视" in channel:
            satellite_channels.append({
                "channel": channel,
                "url": url,
                "logo": orig_logo,
                "group_title": "📡卫视频道"
            })
            continue
            
        # 5. 检查是否属于其他类别（咪咕、动漫等）
        matched_category = None
        for category, keywords in other_categories.items():
            if any(keyword in channel for keyword in keywords):
                matched_category = category
                break
                
        if matched_category:
            other_categories_dict[matched_category].append({
                "channel": channel,
                "url": url,
                "logo": orig_logo,
                "group_title": matched_category
            })
            continue
            
        # 4. 处理地方台频道
        found_province = None
        
        # 精确匹配
        for province, channels in province_channels.items():
            for channel_name in channels:
                if channel_name in channel:
                    found_province = province
                    break
            if found_province:
                break
                
        # 四连字匹配
        if not found_province and len(channel) >= 4:
            province_scores = defaultdict(int)
            for i in range(len(channel) - 3):
                quadgram = channel[i:i+4]
                if quadgram in quadgram_to_province:
                    for province in quadgram_to_province[quadgram]:
                        province_scores[province] += 2
                        
            if province_scores:
                max_score = max(province_scores.values())
                best_provinces = [p for p, s in province_scores.items() if s == max_score]
                found_province = min(best_provinces, key=len) if best_provinces else None
        
        # 匹配成功后加入相应省份
        if found_province:
            # 初始化省份列表（如果尚未存在）
            if found_province not in province_channels_dict:
                province_channels_dict[found_province] = []
                
            province_channels_dict[found_province].append({
                "channel": channel,
                "url": url,
                "logo": orig_logo,
                "group_title": found_province
            })
        else:
            # 6. 其他频道
            other_channels.append({
                "channel": channel,
                "url": url,
                "logo": orig_logo,
                "group_title": "🎯樂玩公社"  # 更改名称
            })

    # --- URL去重逻辑开始 ---
    # 按分组优先级排序 (1.央视 -> 2.央视付费 -> 3.卫视 -> 4.地方频道 -> 5.其他类别 -> 6.其他)
    all_groups = [
        ("📺央视频道", cctv_channels_list),
        ("💰央视付费频道", cctv_pay_channels_list),
        ("📡卫视频道", satellite_channels)
    ]
    
    # 4. 添加地方频道（按预定义省份顺序）
    for province in province_order:
        if province in province_channels_dict:
            all_groups.append((province, province_channels_dict[province]))
    
    # 5. 添加其他类别（按预定义顺序）
    for category in [
        "🎥咪咕视频", "🪁动漫频道", "🚸少儿频道", "🎬影视剧频道",
        "🎮游戏频道", "🎵音乐频道", "🏀体育频道", "🏛经典剧场",
        "🚁直播中国"
    ]:
        if category in other_categories_dict:
            all_groups.append((category, other_categories_dict[category]))
    
    # 6. 添加历年春晚分组到其他频道之前
    if "🏮历年春晚" in other_categories_dict:
        all_groups.append(("🏮历年春晚", other_categories_dict["🏮历年春晚"]))
    
    # 7. 添加乐玩公社
    if other_channels:
        all_groups.append(("🎯樂玩公社", other_channels))

    # 使用字典根据URL去重（保留每个URL第一次出现的频道）
    seen_urls = set()
    deduped_channels = []
    
    for group_title, channels in all_groups:
        if not channels: 
            continue
            
        # 排序当前分组内的频道
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
    # --- URL去重逻辑结束 ---

    # 写入 M3U 文件
    with open(m3u_filename, 'w', encoding='utf-8') as f:
        # 添加带有所需属性的标题行
        f.write("#EXTM3U x-tvg-url=\"https://112114.shrimp.cloudns.biz/epg.xml\" catchup=\"append\" catchup-source=\"?playseek=${(b)yyyyMMddHHmmss}-${(e)yyyyMMddHHmmss}\"\n")
        
        # 写入频道信息
        for channel_info in deduped_channels:
            # 生成频道ID
            channel_id = channel_info['channel'].replace('-', '')
            
            # 处理logo地址
            logo_url = ""
            if channel_info['logo']:
                logo_filename = channel_info['logo'].split("/")[-1]
                logo_url = f"https://itv.shrimp.cloudns.biz/logo/{logo_filename}"
            
            # 写入EXTINF行
            f.write(
                f"#EXTINF:-1 tvg-name=\"{channel_id}\" tvg-logo=\"{logo_url}\" group-title=\"{channel_info['group_title']}\",{channel_info['channel']}\n")
            
            # 写入频道URL
            f.write(f"{channel_info['url']}\n")
            
    print(f"🎉 Generated M3U file: {m3u_filename}")
    
    # 写入结构化的 TXT 文件 (按分组结构输出)
    with open(txt_filename, 'w', encoding='utf-8') as f:
        # 1. 按分组收集频道
        grouped_channels = defaultdict(list)
        for channel_info in deduped_channels:
            grouped_channels[channel_info['group_title']].append(channel_info)
        
        # 2. 定义新的分组排序优先级
        group_order = [
            # 1. 央视频道
            "📺央视频道",
            # 2. 央视付费
            "💰央视付费频道",
            # 3. 卫视频道
            "📡卫视频道",
            # 4. 地方频道
            *province_order,
            # 5. 其他类别
            "🎥咪咕视频", "🪁动漫频道", "🚸少儿频道", "🎬影视剧频道",
            "🎮游戏频道", "🎵音乐频道", "🏀体育频道", "🏛经典剧场",
            "🚁直播中国", 
            # 6. 历年春晚
            "🏮历年春晚",
            # 7. 樂玩公社
            "🎯樂玩公社"
        ]
        
        # 3. 按新优先级输出分组
        for group in group_order:
            if group in grouped_channels and grouped_channels[group]:
                f.write(f"{group},#genre#\n")
                
                # 按频道名称排序并输出
                channels = sorted(grouped_channels[group], key=lambda x: x['channel'])
                for channel_info in channels:
                    f.write(f"{channel_info['channel']},{channel_info['url']}\n")
                
                # 删除已处理的分组
                del grouped_channels[group]
        
        # 4. 处理可能漏掉的分组
        for group, channels in grouped_channels.items():
            if channels:
                f.write(f"{group},#genre#\n")
                channels = sorted(channels, key=lambda x: x['channel'])
                for channel_info in channels:
                    f.write(f"{channel_info['channel']},{channel_info['url']}\n")
                    
    print(f"🎉 Generated structured TXT file: {txt_filename}")


# 主函数：处理多个文件并生成输出文件
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

    # 生成输出文件
    generate_output_files(
        all_valid_urls, 
        cctv_channels, 
        province_channels, 
        CONFIG["output_m3u"],
        CONFIG["output_txt"]
    )


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
        ".github/workflows/iTV/🚁直播中国.txt",
        ".github/workflows/iTV/🏮历年春晚.txt",
        ".github/workflows/iTV/🪁动漫频道.txt"
    ]

    # 执行主函数
    asyncio.run(main(file_urls, cctv_channel_file, province_channel_files))
