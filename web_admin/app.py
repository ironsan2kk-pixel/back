"""
Web admin panel for Channel Access Bot.
"""

from datetime import datetime
import secrets
from typing import AsyncGenerator

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import HTMLResponse

from config import settings
from database import database as db
from database.models import Channel, Payment, User, UserSubscription

app = FastAPI(title="Channel Access Bot Admin")
security = HTTPBasic()


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    if db.async_session is None:
        await db.init_db()
    async with db.async_session() as session:
        yield session


def verify_credentials(credentials: HTTPBasicCredentials = Depends(security)) -> None:
    valid_user = secrets.compare_digest(credentials.username, settings.WEB_ADMIN_USER)
    valid_pass = secrets.compare_digest(credentials.password, settings.WEB_ADMIN_PASSWORD)
    if not (valid_user and valid_pass):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )


@app.on_event("startup")
async def startup_event() -> None:
    await db.init_db()


@app.get("/", response_class=HTMLResponse, dependencies=[Depends(verify_credentials)])
async def dashboard(session: AsyncSession = Depends(get_db_session)) -> HTMLResponse:
    users_total = (await session.execute(select(func.count(User.id)))).scalar() or 0
    channels_total = (await session.execute(select(func.count(Channel.id)))).scalar() or 0
    active_subs = (
        await session.execute(
            select(func.count(UserSubscription.id)).where(
                UserSubscription.status.in_(["active", "trial"])
            )
        )
    ).scalar() or 0
    payments_total = (
        await session.execute(
            select(func.sum(Payment.amount)).where(Payment.status == "paid")
        )
    ).scalar() or 0

    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    html = f"""
    <html>
      <head>
        <title>Channel Access Bot Admin</title>
        <style>
          body {{ font-family: Arial, sans-serif; margin: 40px; }}
          .card {{ padding: 16px; border: 1px solid #ddd; border-radius: 8px; margin-bottom: 16px; }}
          .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; }}
          h1 {{ margin-top: 0; }}
        </style>
      </head>
      <body>
        <h1>Channel Access Bot — Admin</h1>
        <p>Updated: {now}</p>
        <div class="grid">
          <div class="card"><strong>Users</strong><br>{users_total}</div>
          <div class="card"><strong>Channels</strong><br>{channels_total}</div>
          <div class="card"><strong>Active subscriptions</strong><br>{active_subs}</div>
          <div class="card"><strong>Paid revenue (USDT)</strong><br>{payments_total:.2f}</div>
        </div>
        <p><a href="/users">View users</a></p>
      </body>
    </html>
    """
    return HTMLResponse(html)


@app.get("/users", response_class=HTMLResponse, dependencies=[Depends(verify_credentials)])
async def users_list(session: AsyncSession = Depends(get_db_session)) -> HTMLResponse:
    users = (
        await session.execute(select(User).order_by(User.created_at.desc()).limit(50))
    ).scalars().all()

    rows = "".join(
        f"<tr><td>{u.id}</td><td>{u.telegram_id}</td><td>{u.username or ''}</td>"
        f"<td>{u.full_name}</td><td>{u.created_at.strftime('%Y-%m-%d')}</td></tr>"
        for u in users
    )

    html = f"""
    <html>
      <head>
        <title>Users</title>
        <style>
          body {{ font-family: Arial, sans-serif; margin: 40px; }}
          table {{ border-collapse: collapse; width: 100%; }}
          th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
          th {{ background: #f7f7f7; }}
        </style>
      </head>
      <body>
        <h1>Latest users</h1>
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Telegram ID</th>
              <th>Username</th>
              <th>Name</th>
              <th>Created</th>
            </tr>
          </thead>
          <tbody>
            {rows}
          </tbody>
        </table>
        <p><a href="/">Back to dashboard</a></p>
      </body>
    </html>
    """
    return HTMLResponse(html)
