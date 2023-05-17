import pandas as pd
import json

def parse_excel(file):
    # 读取 Excel 文件
    df = pd.read_excel(file)

    # 将缺失值 NaN 替换为空字符串 ''
    df = df.fillna('')

    # 将 DataFrame 转成字典格式
    data = df.to_dict(orient='records')

    # 将字典转成 JSON 格式
    json_data = json.dumps(data)

    # 返回 JSON 格式数据
    return json_data
