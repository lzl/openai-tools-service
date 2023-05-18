## Getting Started

```bash
pip install -r requirements.txt
```

```bash
python app.py
```

## Deployment

```bash
gcloud builds submit --tag gcr.io/withcontextai/openai-tools --project withcontextai
gcloud run deploy --image gcr.io/withcontextai/openai-tools --project withcontextai --platform managed
```
