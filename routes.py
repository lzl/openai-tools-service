from flask import Blueprint, request, jsonify, Response
import os
import openai
import json
import uuid
import random
import time
from google.cloud import tasks_v2
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Attachment, FileContent, FileName, FileType, Disposition, Email
import base64
from utils import parse_excel, generate_excel

global_emails_store = {}
global_sheets_store = {}
global_questions_store = {}
global_answers_store = {}

main_routes = Blueprint('main_routes', __name__)


@main_routes.route('/result', methods=['GET'])
def result_route():
    global global_questions_store
    global global_answers_store
    json_data = {
        "emails": global_emails_store,
        "sheets": global_sheets_store,
        "questions": global_questions_store,
        "answers": global_answers_store
    }
    return jsonify(json_data)


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


@main_routes.route('/ask_all_questions', methods=['POST'])
def ask_all_questions_route():
    data = request.get_json()
    email = data.get('email', [])
    sheets = data.get('sheets', [])
    questions = data.get('questions', [])
    request_id = uuid.uuid4().hex

    global_emails_store
    global_emails_store[request_id] = email

    global global_sheets_store
    global_sheets_store[request_id] = sheets

    tasks_client = tasks_v2.CloudTasksClient()
    parent = tasks_client.queue_path(
        'withcontextai', 'us-west1', 'chat-completions-queue')

    for i, question in enumerate(questions):
        question_id = question.get("id")
        question_text = question.get("text")
        # question_id = uuid.uuid4().hex
        # question_text = question

        payload = json.dumps({
            "request_id": request_id,
            "question_id": question_id,
            "question_text": question_text
        })

        global global_questions_store
        if request_id not in global_questions_store:
            global_questions_store[request_id] = []
        global_questions_store[request_id].append(
            {"id": question_id, "text": question_text})

        task = {
            'http_request': {
                'http_method': 'POST',
                'url': 'https://openai-tools-mmxbwgwwaq-uw.a.run.app/chat_completions_test',
                'headers': {
                    'Content-Type': 'application/json'
                },
                'body': payload.encode(),
            }
        }

        tasks_client.create_task(request={'parent': parent, 'task': task})

    return jsonify({"message": "Tasks created successfully", "request_id": request_id}), 200


@main_routes.route('/chat_completions_test', methods=['POST'])
def chat_completions_test_route():
    data = request.get_data()
    if not data:
        return jsonify({"error": "Invalid request, data not found"}), 400

    data = json.loads(data)
    request_id = data.get("request_id")
    question_id = data.get("question_id")
    question_text = data.get("question_text")

    if not request_id or not question_id or not question_text:
        return jsonify({"error": "Data missing: request_id, question_id, or question_text"}), 400

    # Simulate a 1-minute waiting time
    # time.sleep(60)
    time.sleep(10)

    # Process the question and return a random answer for demonstration purposes
    answer = f"Answer to question {question_id}: {random.choice(['Yes', 'No', 'Maybe'])}"

    # Format the answer and other metadata as a JSON string
    payload = json.dumps({
        "request_id": request_id,
        "question_id": question_id,
        "answer_text": answer
    })

    task = {
        'http_request': {
            'http_method': 'POST',
            'url': 'https://openai-tools-mmxbwgwwaq-uw.a.run.app/answer_collector_test',
            'headers': {
                'Content-Type': 'application/json'
            },
            'body': payload.encode(),
        }
    }

    tasks_client = tasks_v2.CloudTasksClient()
    parent = tasks_client.queue_path(
        'withcontextai', 'us-west1', 'answer-collector-queue')
    tasks_client.create_task(request={'parent': parent, 'task': task})

    return jsonify({"message": f"Answer published for question {question_id}"}), 200


@main_routes.route('/answer_collector_test', methods=['POST'])
def answer_collector_test_route():
    data = request.get_data()
    if not data:
        return jsonify({"error": "Invalid request, data not found"}), 400

    data = json.loads(data)
    request_id = data.get("request_id")
    question_id = data.get("question_id")
    answer_text = data.get("answer_text")

    global global_answers_store
    if request_id not in global_answers_store:
        global_answers_store[request_id] = []
    global_answers_store[request_id].append(
        {"id": question_id, "text": answer_text})

    # delete questions from global_questions_store based by request_id and question_id
    global global_questions_store
    if request_id in global_questions_store:
        global_questions_store[request_id] = [
            question for question in global_questions_store[request_id] if question["id"] != question_id]

    # if not request_id or not question_id or not answer_text:
    #     return jsonify({"error": "Data missing: request_id, question_id, or answer_text"}), 400

    return jsonify({"message": f"Answer published for question {question_id}"}), 200

@main_routes.route('/generate_excel_test', methods=['POST'])
def generate_excel_test_route():
    data = request.get_json()
    request_id = data.get("request_id")
    sheets = global_sheets_store[request_id]
    answers = global_answers_store[request_id]
    print('generate_excel_test')
    print('sheets:', sheets)
    print('answers:', answers)
    # loop sheet with id and row, use id to get answer from answers, insert answer into the row
    json_data = sheets
    for sheet in json_data:
        for answer in answers:
            if sheet["id"] == answer["id"]:
                sheet["row"]["answer"] = answer["text"]
    json_data = [{**item["row"]} for item in json_data]
    print('json_data:', json_data)

    output = generate_excel(json_data)
    # 将 xlsx 文件作为响应发送给客户端
    response = Response(output.read(
    ), mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response.headers.set('Content-Disposition',
                         'attachment', filename='output.xlsx')
    return response


@main_routes.route('/send_email_test', methods=['POST'])
def send_email_test_route():
    data = request.get_json()
    request_id = data.get("request_id")
    email = global_emails_store[request_id]
    excel_data = data.get("excel_data")
    output = generate_excel(excel_data)

    # 使用 base64 对 xlsx 文件进行编码
    data = output.read()
    encoded_data = base64.b64encode(data).decode()

    # 邮件信息
    from_email = Email("chenchongyang@withcontext.ai")  # 发件人
    to_email = Email(email)  # 收件人
    subject = "Sending Test Email with XLSX Attachment"
    content = "Hi, please find the attached xlsx file."

    # 创建附件
    attachment = Attachment()
    attachment.file_content = FileContent(encoded_data)
    attachment.file_type = FileType('application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    attachment.file_name = FileName('output.xlsx')
    attachment.disposition = Disposition('attachment')

    # 创建邮件
    mail = Mail(from_email, to_email, subject, content)
    mail.attachment = attachment

    # 发送邮件
    api_key = os.getenv('SENDGRID_API_KEY')  # 获取你的 SendGrid API 密钥
    sg = SendGridAPIClient(api_key)
    response = sg.send(mail)
    
    return {"message": "Email sent successfully"}, 200

@main_routes.route('/chat_completions', methods=['POST'])
def chat_completions_route():
    # Get the Authorization header value
    auth_header = request.headers.get("Authorization")

    # Check if the header value exists
    if not auth_header:
        return jsonify({"error": "Authorization header is required"}), 401

    # Extract the token by splitting the header value by whitespace (assuming "Bearer" scheme)
    auth_token = auth_header.split(" ")[1]

    is_auth_token_valid = auth_token == os.environ.get("ACCESS_CODE")
    if not is_auth_token_valid:
        return jsonify({"error": "Authorization is not valid"}), 403

    if not request.is_json:
        return jsonify({"error": "JSON data expected"}), 400

    data = request.get_json()

    model = data.get("model", "gpt-3.5-turbo")
    messages = data.get("messages", [])
    temperature = data.get("temperature", 0.7)
    presence_penalty = data.get("presence_penalty", 0)
    frequency_penalty = data.get("frequency_penalty", 0)

    if not (model and messages):
        return jsonify({"error": "model and messages must be provided"}), 400

    try:
        response = openai.ChatCompletion.create(
            model=model,
            messages=messages,
            temperature=temperature,
            presence_penalty=presence_penalty,
            frequency_penalty=frequency_penalty,
        )
        return jsonify(response)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@main_routes.route('/generate_excel', methods=['POST'])
def generate_excel_route():
    json_data = request.get_json()
    output = generate_excel(json_data)
    # 将 xlsx 文件作为响应发送给客户端
    response = Response(output.read(
    ), mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response.headers.set('Content-Disposition',
                         'attachment', filename='output.xlsx')
    return response
