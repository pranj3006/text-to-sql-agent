
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.text_to_sql import answer_question

app = FastAPI(title="Retail Text-to-SQL Baseline")


class QuestionRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1000)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/query")
def query(request: QuestionRequest):
    try:
        return answer_question(request.question)
    except ValueError as exc:
        print("exc",exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        # Log the actual exception in a real application.
        print("exc",exc)
        raise HTTPException(
            status_code=500,
            detail="Unable to generate or execute the query.",
        ) from exc
