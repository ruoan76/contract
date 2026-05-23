# -*- coding: utf-8 -*-
"""仅启动 AI 种子与演示 API（无数据库依赖）。开发联调用。"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import ai_review_seeds, ai_review_demo

app = FastAPI(title="合同平台 AI 种子 API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ai_review_seeds.router, prefix="/api/v1/ai-review", tags=["AI 审查-种子"])
app.include_router(ai_review_demo.router, prefix="/api/v1/ai-review", tags=["AI 审查-演示"])


@app.get("/health")
async def health():
    return {"status": "healthy", "module": "ai-review-seeds"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main_seeds:app", host="0.0.0.0", port=8001, reload=True)
