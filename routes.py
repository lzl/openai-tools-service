from flask import Blueprint, request, jsonify
import openai
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

@main_routes.route('/chat_completions', methods=['POST'])
def chat_completions_route():
    if not request.is_json:
        return jsonify({"error": "JSON data expected"}), 400

    data = request.get_json()

    model = data.get("model")
    messages = data.get("messages")
    temperature = data.get("temperature", 0.6)
    max_tokens = data.get("max_tokens", 100)

    if not (model and messages):
        return jsonify({"error": "model and messages must be provided"}), 400

    try:
        response = openai.ChatCompletion.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        return jsonify(response)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
