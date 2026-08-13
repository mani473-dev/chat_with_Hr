from fastapi import FastAPI

from pydantic import BaseModel

from handler import getOutput


app = FastAPI()


class QuestionRequest(BaseModel):

    question: str


@app.post("/execute")
def execute(
    request: QuestionRequest
):

    return getOutput(
        request.question
    )