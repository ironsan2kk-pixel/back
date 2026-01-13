"""Run the web admin panel."""

import uvicorn

from config import settings


if __name__ == "__main__":
    uvicorn.run(
        "web_admin.app:app",
        host=settings.WEB_ADMIN_HOST,
        port=settings.WEB_ADMIN_PORT,
        reload=settings.WEB_ADMIN_RELOAD,
    )
