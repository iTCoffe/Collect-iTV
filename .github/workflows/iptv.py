# 在匹配逻辑部分替换为以下代码

# 分别构建三连字和双连字的索引
trigram_to_province = defaultdict(set)
bigram_to_province = defaultdict(set)

for province, channels in province_channels.items():
    for channel_name in channels:
        # 添加原始词序的三连字（优先级更高）
        if len(channel_name) >= 3:
            for i in range(len(channel_name) - 2):
                trigram = channel_name[i:i+3]
                trigram_to_province[trigram].add((province, True))  # True表示原始词序
        
        # 添加原始词序的双连字
        if len(channel_name) >= 2:
            for i in range(len(channel_name) - 1):
                bigram = channel_name[i:i+2]
                bigram_to_province[bigram].add((province, True))

# 尝试三连字匹配（按原始词序）
for i in range(len(channel) - 2):
    trigram = channel[i:i+3]
    if trigram in trigram_to_province:
        # 优先选择原始词序匹配的省份
        for province, is_original in trigram_to_province[trigram]:
            if is_original:
                found_province = province
                break
        if found_province:
            break

# 三连字未命中时尝试双连字匹配（按原始词序）
if not found_province:
    for i in range(len(channel) - 1):
        bigram = channel[i:i+2]
        if bigram in bigram_to_province:
            for province, is_original in bigram_to_province[bigram]:
                if is_original:
                    found_province = province
                    break
            if found_province:
                break

# 添加非词序匹配作为后备
if not found_province:
    # 遍历所有省份的所有频道名称进行精确匹配
    for province, channels in province_channels.items():
        for channel_name in channels:
            if channel_name in channel:  # 完整频道名称出现在待匹配频道字符串中
                found_province = province
                break
        if found_province:
            break
