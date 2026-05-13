from __future__ import annotations

import asyncio
import os

from sqlalchemy import select

from app.core.security import Role, hash_password, verify_password
from app.db.models.user import User
from app.db.session import AsyncSessionLocal


async def seed_admin() -> None:
    email = os.getenv("ADMIN_EMAIL", "admin@example.com")
    password = os.getenv("ADMIN_PASSWORD", "admin123")
    full_name = os.getenv("ADMIN_FULL_NAME", "Administrador OfficeJoe")

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if user is None:
            session.add(
                User(
                    email=email,
                    full_name=full_name,
                    hashed_password=hash_password(password),
                    role=Role.ADMIN.value,
                    is_active=True,
                    is_superuser=True,
                )
            )
            await session.commit()
            print(f"Admin user created: {email}")
            return

        changed = False
        if not verify_password(password, user.hashed_password):
            user.hashed_password = hash_password(password)
            changed = True
        if user.role != Role.ADMIN.value:
            user.role = Role.ADMIN.value
            changed = True
        if not user.is_active:
            user.is_active = True
            changed = True
        if not user.is_superuser:
            user.is_superuser = True
            changed = True

        if changed:
            await session.commit()
            print(f"Admin user updated: {email}")
        else:
            print(f"Admin user ready: {email}")


if __name__ == "__main__":
    asyncio.run(seed_admin())
