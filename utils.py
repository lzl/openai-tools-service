import io
import pandas as pd
import json
import xlsxwriter

def parse_excel(file):
    # 读取 Excel 文件
    df = pd.read_excel(file)

    # 将缺失值 NaN 替换为空字符串 ''
    df = df.fillna('')

    # 将 DataFrame 转成字典格式
    data = df.to_dict(orient='records')

    return data

    # # 将字典转成 JSON 格式
    # json_data = json.dumps(data)

    # # 返回 JSON 格式数据
    # return json_data

def generate_excel(json_data):
    # 创建一个 xlsx 文件并添加一个工作表
    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    worksheet = workbook.add_worksheet()

    # 写入表头
    headers = [row[0] for row in json_data[0]]
    for col_num, header in enumerate(headers):
        worksheet.write(0, col_num, header)

    # 写入 JSON 数据到 xlsx 文件
    row_num = 1
    for data in json_data:
        for col_num, value in enumerate(data):
            worksheet.write(row_num, col_num, value[1])
        row_num += 1

    # 关闭 xlsx 文件
    workbook.close()

    # 将 xlsx 文件返回
    output.seek(0)
    return output
