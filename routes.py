from flask import Blueprint, request, jsonify, Response
import os
import openai
import json
import uuid
import random
import time
from google.cloud import tasks_v2
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import *
import base64
from utils import parse_excel, generate_excel
from google.cloud import firestore

db = firestore.Client(project='withcontextai')

# global_emails_store = {}
# global_sheets_store = {}
# global_questions_store = {}
# global_answers_store = {}

main_routes = Blueprint('main_routes', __name__)


@main_routes.route('/result', methods=['GET'])
def result_route():
    request_id = request.args.get('request_id')  # 获取URL中的请求参数
    if request_id:
        data = db.collection('requests').document(
            request_id).get()  # 使用request_id获取firestore文档
        json_data = data.to_dict()
        return jsonify(json_data)
    else:
        requests_ref = db.collection('requests').order_by(
            'created_at', direction=firestore.Query.DESCENDING).limit(10)
        requests_data = []
        for doc in requests_ref.stream():  # 遍历requests collection中的每个文档
            requests_data.append({"id": doc.id, "doc": doc.to_dict()})
        return jsonify(requests_data)

    # global global_questions_store
    # global global_answers_store
    # json_data = {
    #     "emails": global_emails_store,
    #     "sheets": global_sheets_store,
    #     "questions": global_questions_store,
    #     "answers": global_answers_store
    # }
    # return jsonify(json_data)


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
    # request_id = uuid.uuid4().hex

    request_data = {
        "email": email,
        "sheets": sheets,
        "questions": questions,
        "answers": []
    }
    # db.collection('requests').document(request_id).set(request_data)
    created_at, request_ref = db.collection('requests').add(request_data)
    request_id = request_ref.id

    # global global_emails_store
    # global_emails_store[request_id] = email

    # global global_sheets_store
    # global_sheets_store[request_id] = sheets

    tasks_client = tasks_v2.CloudTasksClient()
    parent = tasks_client.queue_path(
        'withcontextai', 'us-west1', 'chat-completions-queue')

    for i, question in enumerate(questions):
        question_id = question.get("id")
        question_text = question.get("text")
        # question_id = uuid.uuid4().hex
        # question_text = question

        payload = json.dumps({
            "created_at": created_at,
            "request_id": request_id,
            "question_id": question_id,
            "question_text": question_text
        })

        # global global_questions_store
        # if request_id not in global_questions_store:
        #     global_questions_store[request_id] = []
        # global_questions_store[request_id].append(
        #     {"id": question_id, "text": question_text})

        task = {
            'http_request': {
                'http_method': 'POST',
                'url': 'https://openai-tools-mmxbwgwwaq-uw.a.run.app/chat_completions_async',
                'headers': {
                    'Content-Type': 'application/json',
                    'Authorization': 'Bearer ' + os.environ.get("ACCESS_CODE"),
                },
                'body': payload.encode(),
            }
        }

        tasks_client.create_task(request={'parent': parent, 'task': task})

    return jsonify({"message": "Tasks created successfully", "request_id": request_id}), 200


@main_routes.route('/chat_completions_async', methods=['POST'])
def chat_completions_async_route():
    data = request.get_json()
    request_id = data.get("request_id")
    question_id = data.get("question_id")
    question_text = data.get("question_text")

    if not request_id or not question_id or not question_text:
        return jsonify({"error": "Data missing: request_id, question_id, or question_text"}), 400

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

    # data = request.get_json()

    model = data.get("model", "gpt-3.5-turbo")
    # messages = data.get("messages", [])
    messages = [{"role": "system", "content": "You are ChatGPT, a large language model trained by OpenAI."}, {
        "role": "user", "content": question_text}]
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
        # return jsonify(response)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    answer = response.get("choices", [])[0].get("message", {}).get("content")

    # Process the question and return a random answer for demonstration purposes
    # answer_choice = random.choice(['Yes', 'No', 'Maybe'])
    # if answer_choice == "Maybe":
    # return jsonify({"error": "Cannot answer with Maybe"}), 400
    # answer = f"Answer to question {question_id}: {answer_choice}"

    # Format the answer and other metadata as a JSON string
    payload = json.dumps({
        "request_id": request_id,
        "question_id": question_id,
        "answer_text": answer
    })

    task = {
        'http_request': {
            'http_method': 'POST',
            'url': 'https://openai-tools-mmxbwgwwaq-uw.a.run.app/answer_collector',
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


@main_routes.route('/answer_collector', methods=['POST'])
def answer_collector_route():
    data = request.get_json()

    # 从请求中获取 request_id, question_id 和 answer_text
    request_id = data.get("request_id")
    question_id = data.get("question_id")
    answer_text = data.get("answer_text")

    request_data = db.collection('requests').document(
        request_id).get().to_dict()

    answers = request_data["answers"]
    answers.append({"id": question_id, "text": answer_text})
    db.collection('requests').document(request_id).update({"answers": answers})

    questions = request_data["questions"]
    questions = [
        question for question in questions if question["id"] != question_id]
    db.collection('requests').document(
        request_id).update({"questions": questions})

    # # 添加 answer_text 到全局变量中
    # global global_answers_store
    # if request_id not in global_answers_store:
    #     global_answers_store[request_id] = []
    # global_answers_store[request_id].append(
    #     {"id": question_id, "text": answer_text})

    # # 删除 global_questions_store 中的对应 question_id 的数据
    # global global_questions_store
    # if request_id in global_questions_store:
    #     global_questions_store[request_id] = [
    #         question for question in global_questions_store[request_id] if question["id"] != question_id]

    # 如果问题都回答完了，触发发送邮件任务
    # if request_id in global_questions_store and len(global_questions_store[request_id]) == 0:
    if request_data is not None and len(questions) == 0:
        payload = json.dumps({
            "request_id": request_id,
        })

        task = {
            'http_request': {
                'http_method': 'POST',
                'url': 'https://openai-tools-mmxbwgwwaq-uw.a.run.app/send_answers_email',
                'headers': {
                    'Content-Type': 'application/json'
                },
                'body': payload.encode(),
            }
        }

        tasks_client = tasks_v2.CloudTasksClient()
        parent = tasks_client.queue_path(
            'withcontextai', 'us-west1', 'send-answers-email-queue')
        tasks_client.create_task(request={'parent': parent, 'task': task})

    return jsonify({"message": f"Answer published for question {question_id}"}), 200


@main_routes.route('/send_answers_email', methods=['POST'])
def send_answers_email_route():
    data = request.get_json()

    # 从请求中获取 request_id
    request_id = data.get("request_id")

    data = db.collection('requests').document(request_id).get().to_dict()
    sheets = data["sheets"]
    answers = data["answers"]
    email = data["email"]
    # # 从全局变量中获取 sheets, answers 和 email
    # sheets = global_sheets_store.get(request_id)
    # answers = global_answers_store.get(request_id)
    # email = global_emails_store.get(request_id)

    # 整合 sheets 和 answers 数据
    for sheet in sheets:
        for answer in answers:
            if sheet["id"] == answer["id"]:
                sheet["row"]["answer"] = answer["text"]
    json_data = [{**item["row"]} for item in sheets]

    # 生成 excel 表格并保存到内存
    output = generate_excel(json_data)

    # 使用 base64 对 xlsx 文件进行编码
    data = output.read()
    encoded_data = base64.b64encode(data).decode()

    sg = SendGridAPIClient(api_key=os.environ.get('SENDGRID_API_KEY'))

    # 创建邮件附件
    attachment = Attachment()
    attachment.file_content = FileContent(encoded_data)
    attachment.file_type = FileType(
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    attachment.file_name = FileName('output.xlsx')
    attachment.disposition = Disposition('attachment')

    # 创建邮件
    from_email = From("chenchongyang@withcontext.ai")  # 发件人
    to_email = To(email)  # 收件人
    subject = "生成的Excel文件"
    body = Content("text/plain", "您好，附上您要求的 Excel 文件。")
    mail = Mail(from_email, to_email, subject, body)
    mail.add_attachment(attachment)

    try:
        # 发送邮件
        response = sg.send(mail)
        if response.status_code != 202:  # 如果发送邮件失败，返回报错
            return {"error": f"Failed to send email, error code: {response.status_code}"}, 400
    except Exception as e:
        return {"error": f"Failed to send email: {e}"}, 400

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
