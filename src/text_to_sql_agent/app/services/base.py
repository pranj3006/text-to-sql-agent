"""
Services hold business logic and orchestrate repositories, cache, and
external calls. Controllers call services; services never touch the DB
session directly except via repositories (keeps persistence swappable
and testable via repository mocks).
"""
from sqlalchemy.ext.asyncio import AsyncSession


class BaseService:
    def __init__(self, session: AsyncSession):
        self.session = session
