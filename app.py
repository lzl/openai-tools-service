from flask import Flask, request, jsonify
import pandas as pd
import json

app = Flask(__name__)

def parse_excel(file):
    # 读取 Excel 文件
    df = pd.read_excel(file)

    # 将 DataFrame 转成字典格式
    data = df.to_dict(orient='records')

    # 将字典转成 JSON 格式
    json_data = json.dumps(data)

    # 返回 JSON 格式数据
    return json_data

@app.route('/parse_excel', methods=['POST'])
def upload_file():
    # 检查是否上传了文件
    if 'file' not in request.files:
        return 'No file uploaded'

    file = request.files['file']

    # 检查文件是否符合要求
    if file.filename == '':
        return 'No file selected'
    if not file.filename.endswith('.xlsx'):
        return 'Invalid file type'

    # 调用解析函数
    json_data = parse_excel(file)

    # 返回 JSON 格式数据
    return jsonify(json_data)

if __name__ == '__main__':
    app.run(debug=True)
