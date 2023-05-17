from flask import Flask
from flask_cors import CORS
import os
import openai

openai.api_key = os.environ.get("OPENAI_API_KEY")
app_env = os.environ.get('APP_ENV')

def create_app():
    app = Flask(__name__)
    CORS(app)  # 允许跨域访问

    from routes import main_routes

    app.register_blueprint(main_routes)

    return app

if __name__ == '__main__':
    app = create_app()
    if app_env == "production":
        import os
        os.system("gunicorn -w 4 --bind 0.0.0.0:8080 app:app")
    else:
        app.run(debug=True)
