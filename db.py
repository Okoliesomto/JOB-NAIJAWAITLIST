import os
import asyncpg
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # swap "*" for your Netlify URL once it's stable
    allow_methods=["POST"],
    allow_headers=["*"],
)

DATABASE_URL = os.environ["DATABASE_URL"]  # Railway injects this automatically
pool = None

@app.on_event("startup")
async def startup():
    global pool
    pool = await asyncpg.create_pool(DATABASE_URL)
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS waitlist_signups (
                id SERIAL PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                role TEXT NOT NULL,
                created_at TIMESTAMPTZ DEFAULT now()
            )
        """)

@app.on_event("shutdown")
async def shutdown():
    await pool.close()

class WaitlistIn(BaseModel):
    email: EmailStr
    role: str

@app.post("/api/waitlist")
async def join_waitlist(payload: WaitlistIn):
    async with pool.acquire() as conn:
        try:
            await conn.execute(
                "INSERT INTO waitlist_signups (email, role) VALUES ($1, $2)",
                payload.email, payload.role
            )
        except asyncpg.UniqueViolationError:
            raise HTTPException(409, "Already on the list")
    return {"status": "saved"}