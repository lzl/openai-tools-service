from flask import Blueprint, request, jsonify
from utils import parse_excel

main_routes = Blueprint('main_routes', __name__)

@main_routes.route('/parse_excel', methods=['POST'])
def parse_excel_route():
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
