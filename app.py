from flask import Flask
from flask_cors import CORS
import os
import openai

openai.api_key = os.environ.get("OPENAI_API_KEY")

def create_app():
    app = Flask(__name__)
    CORS(app)  # 允许跨域访问

    from routes import main_routes

    app.register_blueprint(main_routes)

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
