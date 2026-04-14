"""Seed minimal users for dev. Idempotent.

Usage (inside backend container):
    python -m scripts.seed_users
"""

from __future__ import annotations

import asyncio

from app.db.models.user import UserRole
from app.db.session import AsyncSessionLocal
from app.services import users as users_svc

SEED = [
    ("paciente@hsll.es", "paciente", UserRole.paciente, "Paciente Demo"),
    ("clinico@hsll.es", "clinico", UserRole.clinico, "Clínico Demo"),
    ("admin@hsll.es", "admin", UserRole.admin, "Admin Demo"),
    ("auditor@hsll.es", "auditor", UserRole.auditor, "Auditor Demo"),
]


async def main() -> None:
    async with AsyncSessionLocal() as session:
        created = 0
        for email, password, role, full_name in SEED:
            existing = await users_svc.get_by_email(session, email)
            if existing:
                continue
            await users_svc.create(
                session, email=email, password=password, role=role, full_name=full_name
            )
            created += 1
        await session.commit()
        print(f"seed done: created={created} skipped={len(SEED) - created}")


if __name__ == "__main__":
    asyncio.run(main())
