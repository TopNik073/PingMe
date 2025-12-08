from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

import uvicorn

app = FastAPI()


def load_openapi_spec():
    import yaml

    with open('./openapi.yml', 'r') as spec:
        return yaml.safe_load(spec)


app.openapi_schema = load_openapi_spec()


@app.get('/')
def index():
    return 'Test openapi spec'


uvicorn.run(app)
