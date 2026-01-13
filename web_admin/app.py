"""
═══════════════════════════════════════════════════════════════════════════════
🌐 WEB ADMIN - MAIN APP
═══════════════════════════════════════════════════════════════════════════════
"""

from fastapi import FastAPI, Request, Depends, HTTPException, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from datetime import datetime, timedelta
from typing import Optional
import os
import sys

# Добавляем родительскую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings

# Синхронный движок для веб-админки
sync_database_url = settings.DATABASE_URL.replace("+aiosqlite", "").replace("sqlite+aiosqlite", "sqlite")
engine = create_engine(sync_database_url, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Импорт моделей после создания движка
from database.models import (
    Base, User, Channel, SubscriptionPlan, SubscriptionPackage,
    UserSubscription, Payment, Promocode, ActivityLog, Broadcast
)

# ═══════════════════════════════════════════════════════════════════════════════
# 🚀 ИНИЦИАЛИЗАЦИЯ
# ═══════════════════════════════════════════════════════════════════════════════

app = FastAPI(title="Bot Admin Panel", docs_url=None, redoc_url=None)

# Пути
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")


# ═══════════════════════════════════════════════════════════════════════════════
# 🔧 ЗАВИСИМОСТИ
# ═══════════════════════════════════════════════════════════════════════════════

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ═══════════════════════════════════════════════════════════════════════════════
# 📊 DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    """Главная страница - дашборд со статистикой."""

    # Основная статистика
    total_users = db.query(User).count()
    active_users_24h = db.query(User).filter(
        User.last_activity >= datetime.utcnow() - timedelta(hours=24)
    ).count()
    blocked_users = db.query(User).filter(User.is_blocked == True).count()

    # Подписки
    active_subscriptions = db.query(UserSubscription).filter(
        UserSubscription.is_active == True
    ).count()

    # Платежи
    total_payments = db.query(Payment).filter(Payment.status == "paid").count()
    total_revenue = db.query(Payment).filter(Payment.status == "paid").with_entities(
        db.query(Payment.amount).filter(Payment.status == "paid")
    ).count()

    # За сегодня
    today = datetime.utcnow().date()
    new_users_today = db.query(User).filter(
        User.created_at >= datetime.combine(today, datetime.min.time())
    ).count()
    payments_today = db.query(Payment).filter(
        Payment.created_at >= datetime.combine(today, datetime.min.time()),
        Payment.status == "paid"
    ).count()

    # Каналы
    total_channels = db.query(Channel).filter(Channel.is_active == True).count()

    # Последние действия
    recent_logs = db.query(ActivityLog).order_by(
        ActivityLog.created_at.desc()
    ).limit(10).all()

    stats = {
        "total_users": total_users,
        "active_users_24h": active_users_24h,
        "blocked_users": blocked_users,
        "active_subscriptions": active_subscriptions,
        "total_payments": total_payments,
        "new_users_today": new_users_today,
        "payments_today": payments_today,
        "total_channels": total_channels,
    }

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "stats": stats,
        "recent_logs": recent_logs,
        "page": "dashboard"
    })


# ═══════════════════════════════════════════════════════════════════════════════
# 👥 ПОЛЬЗОВАТЕЛИ
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/users", response_class=HTMLResponse)
async def users_list(
    request: Request,
    page: int = Query(1, ge=1),
    search: str = Query(""),
    filter_type: str = Query("all"),
    db: Session = Depends(get_db)
):
    """Список пользователей."""
    per_page = 20
    offset = (page - 1) * per_page

    query = db.query(User)

    # Поиск
    if search:
        query = query.filter(
            (User.username.ilike(f"%{search}%")) |
            (User.first_name.ilike(f"%{search}%")) |
            (User.telegram_id.ilike(f"%{search}%"))
        )

    # Фильтры
    if filter_type == "blocked":
        query = query.filter(User.is_blocked == True)
    elif filter_type == "admin":
        query = query.filter(User.is_admin == True)
    elif filter_type == "with_subs":
        subquery = db.query(UserSubscription.user_id).filter(UserSubscription.is_active == True)
        query = query.filter(User.id.in_(subquery))

    total = query.count()
    users = query.order_by(User.created_at.desc()).offset(offset).limit(per_page).all()

    total_pages = (total + per_page - 1) // per_page

    return templates.TemplateResponse("users.html", {
        "request": request,
        "users": users,
        "page": "users",
        "current_page": page,
        "total_pages": total_pages,
        "search": search,
        "filter_type": filter_type,
        "total": total
    })


@app.get("/users/{user_id}", response_class=HTMLResponse)
async def user_detail(request: Request, user_id: int, db: Session = Depends(get_db)):
    """Детали пользователя."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Подписки
    subscriptions = db.query(UserSubscription).filter(
        UserSubscription.user_id == user_id
    ).all()

    # Платежи
    payments = db.query(Payment).filter(
        Payment.user_id == user_id
    ).order_by(Payment.created_at.desc()).limit(10).all()

    # Рефералы
    referrals = db.query(User).filter(User.referred_by == user_id).all()

    # Активность
    logs = db.query(ActivityLog).filter(
        ActivityLog.user_id == user_id
    ).order_by(ActivityLog.created_at.desc()).limit(20).all()

    return templates.TemplateResponse("user_detail.html", {
        "request": request,
        "user": user,
        "subscriptions": subscriptions,
        "payments": payments,
        "referrals": referrals,
        "logs": logs,
        "page": "users"
    })


@app.post("/users/{user_id}/toggle-block")
async def toggle_user_block(user_id: int, db: Session = Depends(get_db)):
    """Заблокировать/разблокировать пользователя."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_blocked = not user.is_blocked
    db.commit()

    return RedirectResponse(url=f"/users/{user_id}", status_code=303)


@app.post("/users/{user_id}/toggle-admin")
async def toggle_user_admin(user_id: int, db: Session = Depends(get_db)):
    """Назначить/снять админа."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_admin = not user.is_admin
    db.commit()

    return RedirectResponse(url=f"/users/{user_id}", status_code=303)


@app.post("/users/{user_id}/add-balance")
async def add_user_balance(
    user_id: int,
    amount: float = Form(...),
    db: Session = Depends(get_db)
):
    """Добавить баланс пользователю."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.balance = (user.balance or 0) + amount
    db.commit()

    return RedirectResponse(url=f"/users/{user_id}", status_code=303)


# ═══════════════════════════════════════════════════════════════════════════════
# 📺 КАНАЛЫ
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/channels", response_class=HTMLResponse)
async def channels_list(request: Request, db: Session = Depends(get_db)):
    """Список каналов."""
    channels = db.query(Channel).order_by(Channel.created_at.desc()).all()

    # Статистика по каждому каналу
    for channel in channels:
        channel.subscribers_count = db.query(UserSubscription).filter(
            UserSubscription.channel_id == channel.id,
            UserSubscription.is_active == True
        ).count()

    return templates.TemplateResponse("channels.html", {
        "request": request,
        "channels": channels,
        "page": "channels"
    })


@app.get("/channels/add", response_class=HTMLResponse)
async def channel_add_form(request: Request):
    """Форма добавления канала."""
    return templates.TemplateResponse("channel_form.html", {
        "request": request,
        "channel": None,
        "page": "channels"
    })


@app.post("/channels/add")
async def channel_add(
    name_ru: str = Form(...),
    name_en: str = Form(""),
    telegram_id: int = Form(...),
    username: str = Form(""),
    description_ru: str = Form(""),
    description_en: str = Form(""),
    db: Session = Depends(get_db)
):
    """Добавить канал."""
    channel = Channel(
        name_ru=name_ru,
        name_en=name_en or name_ru,
        telegram_id=telegram_id,
        username=username or None,
        description_ru=description_ru,
        description_en=description_en,
        is_active=True
    )
    db.add(channel)
    db.commit()

    return RedirectResponse(url="/channels", status_code=303)


@app.get("/channels/{channel_id}", response_class=HTMLResponse)
async def channel_detail(request: Request, channel_id: int, db: Session = Depends(get_db)):
    """Детали канала."""
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    # Тарифы
    plans = db.query(SubscriptionPlan).filter(
        SubscriptionPlan.channel_id == channel_id
    ).all()

    # Подписчики
    subscribers = db.query(UserSubscription).filter(
        UserSubscription.channel_id == channel_id,
        UserSubscription.is_active == True
    ).all()

    return templates.TemplateResponse("channel_detail.html", {
        "request": request,
        "channel": channel,
        "plans": plans,
        "subscribers": subscribers,
        "page": "channels"
    })


@app.get("/channels/{channel_id}/edit", response_class=HTMLResponse)
async def channel_edit_form(request: Request, channel_id: int, db: Session = Depends(get_db)):
    """Форма редактирования канала."""
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    return templates.TemplateResponse("channel_form.html", {
        "request": request,
        "channel": channel,
        "page": "channels"
    })


@app.post("/channels/{channel_id}/edit")
async def channel_edit(
    channel_id: int,
    name_ru: str = Form(...),
    name_en: str = Form(""),
    telegram_id: int = Form(...),
    username: str = Form(""),
    description_ru: str = Form(""),
    description_en: str = Form(""),
    is_active: bool = Form(False),
    db: Session = Depends(get_db)
):
    """Редактировать канал."""
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    channel.name_ru = name_ru
    channel.name_en = name_en or name_ru
    channel.telegram_id = telegram_id
    channel.username = username or None
    channel.description_ru = description_ru
    channel.description_en = description_en
    channel.is_active = is_active
    db.commit()

    return RedirectResponse(url=f"/channels/{channel_id}", status_code=303)


@app.post("/channels/{channel_id}/delete")
async def channel_delete(channel_id: int, db: Session = Depends(get_db)):
    """Удалить канал."""
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if channel:
        db.delete(channel)
        db.commit()

    return RedirectResponse(url="/channels", status_code=303)


# ═══════════════════════════════════════════════════════════════════════════════
# 💰 ТАРИФЫ
# ═══════════════════════════════════════════════════════════════════════════════

@app.post("/channels/{channel_id}/plans/add")
async def plan_add(
    channel_id: int,
    months: int = Form(...),
    price: float = Form(...),
    db: Session = Depends(get_db)
):
    """Добавить тариф."""
    plan = SubscriptionPlan(
        channel_id=channel_id,
        months=months,
        price=price,
        is_active=True
    )
    db.add(plan)
    db.commit()

    return RedirectResponse(url=f"/channels/{channel_id}", status_code=303)


@app.post("/plans/{plan_id}/delete")
async def plan_delete(plan_id: int, db: Session = Depends(get_db)):
    """Удалить тариф."""
    plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.id == plan_id).first()
    channel_id = plan.channel_id if plan else None

    if plan:
        db.delete(plan)
        db.commit()

    return RedirectResponse(url=f"/channels/{channel_id}" if channel_id else "/channels", status_code=303)


# ═══════════════════════════════════════════════════════════════════════════════
# 📦 ПАКЕТЫ
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/packages", response_class=HTMLResponse)
async def packages_list(request: Request, db: Session = Depends(get_db)):
    """Список пакетов."""
    packages = db.query(SubscriptionPackage).all()

    return templates.TemplateResponse("packages.html", {
        "request": request,
        "packages": packages,
        "page": "packages"
    })


# ═══════════════════════════════════════════════════════════════════════════════
# 🎟️ ПРОМОКОДЫ
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/promocodes", response_class=HTMLResponse)
async def promocodes_list(request: Request, db: Session = Depends(get_db)):
    """Список промокодов."""
    promocodes = db.query(Promocode).order_by(Promocode.created_at.desc()).all()

    return templates.TemplateResponse("promocodes.html", {
        "request": request,
        "promocodes": promocodes,
        "page": "promocodes"
    })


@app.post("/promocodes/add")
async def promocode_add(
    code: str = Form(...),
    discount_type: str = Form(...),
    discount_value: float = Form(...),
    max_uses: int = Form(0),
    expires_at: str = Form(""),
    db: Session = Depends(get_db)
):
    """Добавить промокод."""
    promo = Promocode(
        code=code.upper(),
        discount_type=discount_type,
        discount_value=discount_value,
        max_uses=max_uses if max_uses > 0 else None,
        expires_at=datetime.fromisoformat(expires_at) if expires_at else None,
        is_active=True
    )
    db.add(promo)
    db.commit()

    return RedirectResponse(url="/promocodes", status_code=303)


@app.post("/promocodes/{promo_id}/toggle")
async def promocode_toggle(promo_id: int, db: Session = Depends(get_db)):
    """Включить/выключить промокод."""
    promo = db.query(Promocode).filter(Promocode.id == promo_id).first()
    if promo:
        promo.is_active = not promo.is_active
        db.commit()

    return RedirectResponse(url="/promocodes", status_code=303)


@app.post("/promocodes/{promo_id}/delete")
async def promocode_delete(promo_id: int, db: Session = Depends(get_db)):
    """Удалить промокод."""
    promo = db.query(Promocode).filter(Promocode.id == promo_id).first()
    if promo:
        db.delete(promo)
        db.commit()

    return RedirectResponse(url="/promocodes", status_code=303)


# ═══════════════════════════════════════════════════════════════════════════════
# 💳 ПЛАТЕЖИ
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/payments", response_class=HTMLResponse)
async def payments_list(
    request: Request,
    page: int = Query(1, ge=1),
    status: str = Query("all"),
    db: Session = Depends(get_db)
):
    """Список платежей."""
    per_page = 20
    offset = (page - 1) * per_page

    query = db.query(Payment)

    if status != "all":
        query = query.filter(Payment.status == status)

    total = query.count()
    payments = query.order_by(Payment.created_at.desc()).offset(offset).limit(per_page).all()

    # Добавляем информацию о пользователях
    for payment in payments:
        payment.user = db.query(User).filter(User.id == payment.user_id).first()

    total_pages = (total + per_page - 1) // per_page

    # Статистика
    total_revenue = db.query(Payment).filter(Payment.status == "paid").count()

    return templates.TemplateResponse("payments.html", {
        "request": request,
        "payments": payments,
        "page": "payments",
        "current_page": page,
        "total_pages": total_pages,
        "status": status,
        "total": total
    })


# ═══════════════════════════════════════════════════════════════════════════════
# 📢 РАССЫЛКИ
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/broadcasts", response_class=HTMLResponse)
async def broadcasts_list(request: Request, db: Session = Depends(get_db)):
    """Список рассылок."""
    broadcasts = db.query(Broadcast).order_by(Broadcast.created_at.desc()).all()

    return templates.TemplateResponse("broadcasts.html", {
        "request": request,
        "broadcasts": broadcasts,
        "page": "broadcasts"
    })


@app.get("/broadcasts/new", response_class=HTMLResponse)
async def broadcast_form(request: Request, db: Session = Depends(get_db)):
    """Форма создания рассылки."""
    total_users = db.query(User).filter(User.is_blocked == False).count()

    return templates.TemplateResponse("broadcast_form.html", {
        "request": request,
        "total_users": total_users,
        "page": "broadcasts"
    })


# ═══════════════════════════════════════════════════════════════════════════════
# 📋 ЛОГИ
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/logs", response_class=HTMLResponse)
async def logs_list(
    request: Request,
    page: int = Query(1, ge=1),
    action: str = Query(""),
    db: Session = Depends(get_db)
):
    """Список логов активности."""
    per_page = 50
    offset = (page - 1) * per_page

    query = db.query(ActivityLog)

    if action:
        query = query.filter(ActivityLog.action == action)

    total = query.count()
    logs = query.order_by(ActivityLog.created_at.desc()).offset(offset).limit(per_page).all()

    # Добавляем информацию о пользователях
    for log in logs:
        log.user = db.query(User).filter(User.id == log.user_id).first()

    total_pages = (total + per_page - 1) // per_page

    # Уникальные действия для фильтра
    actions = db.query(ActivityLog.action).distinct().all()
    actions = [a[0] for a in actions]

    return templates.TemplateResponse("logs.html", {
        "request": request,
        "logs": logs,
        "page": "logs",
        "current_page": page,
        "total_pages": total_pages,
        "action": action,
        "actions": actions,
        "total": total
    })


# ═══════════════════════════════════════════════════════════════════════════════
# 👥 РЕФЕРАЛЫ
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/referrals", response_class=HTMLResponse)
async def referrals_stats(request: Request, db: Session = Depends(get_db)):
    """Статистика реферальной программы."""

    # Топ рефереров
    from sqlalchemy import func

    top_referrers = db.query(
        User,
        func.count(User.id).label("referral_count")
    ).join(
        User, User.referred_by == User.id, isouter=True
    ).group_by(User.id).having(
        func.count(User.id) > 0
    ).order_by(func.count(User.id).desc()).limit(20).all()

    # Общая статистика
    total_referrals = db.query(User).filter(User.referred_by.isnot(None)).count()
    users_with_referrals = db.query(User.referred_by).filter(
        User.referred_by.isnot(None)
    ).distinct().count()

    return templates.TemplateResponse("referrals.html", {
        "request": request,
        "top_referrers": top_referrers,
        "total_referrals": total_referrals,
        "users_with_referrals": users_with_referrals,
        "page": "referrals"
    })


# ═══════════════════════════════════════════════════════════════════════════════
# ⚙️ НАСТРОЙКИ
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    """Страница настроек."""
    return templates.TemplateResponse("settings.html", {
        "request": request,
        "settings": settings,
        "page": "settings"
    })


# ═══════════════════════════════════════════════════════════════════════════════
# 📊 API ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/stats")
async def api_stats(db: Session = Depends(get_db)):
    """API: статистика для графиков."""
    from sqlalchemy import func

    # Регистрации за последние 7 дней
    week_ago = datetime.utcnow() - timedelta(days=7)
    daily_registrations = db.query(
        func.date(User.created_at).label("date"),
        func.count(User.id).label("count")
    ).filter(
        User.created_at >= week_ago
    ).group_by(func.date(User.created_at)).all()

    # Платежи за последние 7 дней
    daily_payments = db.query(
        func.date(Payment.created_at).label("date"),
        func.count(Payment.id).label("count"),
        func.sum(Payment.amount).label("amount")
    ).filter(
        Payment.created_at >= week_ago,
        Payment.status == "paid"
    ).group_by(func.date(Payment.created_at)).all()

    return {
        "registrations": [{"date": str(r.date), "count": r.count} for r in daily_registrations],
        "payments": [{"date": str(p.date), "count": p.count, "amount": float(p.amount or 0)} for p in daily_payments]
    }


# ═══════════════════════════════════════════════════════════════════════════════
# 🚀 ЗАПУСК
# ═══════════════════════════════════════════════════════════════════════════════

def run_admin(host: str = "127.0.0.1", port: int = 8080):
    """Запуск веб-админки."""
    import uvicorn
    print(f"\n🌐 Web Admin Panel запущена: http://{host}:{port}\n")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run_admin()
