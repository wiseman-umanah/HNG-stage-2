#!/usr/bin/python3
"""Database configuration helpers."""

from contextlib import contextmanager
from dotenv import load_dotenv
from os import getenv
from typing import Iterator

from sqlmodel import Session, SQLModel, create_engine

# load_dotenv()

DATABASE_URL = getenv("DB_URL", "sqlite:///./countries.db")


def _create_engine():
	connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
	return create_engine(DATABASE_URL, echo=False, connect_args=connect_args)


engine = _create_engine()


def init_db() -> None:
	"""Create database tables."""
	SQLModel.metadata.create_all(engine)


@contextmanager
def session_scope() -> Iterator[Session]:
	"""Provide a transactional scope around a series of operations."""
	session = Session(engine)
	try:
		yield session
		session.commit()
	except Exception:
		session.rollback()
		raise
	finally:
		session.close()


def get_session() -> Iterator[Session]:
	"""FastAPI dependency that yields a session."""
	with Session(engine) as session:
		# FastAPI handles closing the generator context for us.
		yield session
	
