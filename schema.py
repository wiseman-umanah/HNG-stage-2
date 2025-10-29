#!/usr/bin/python3
"""Pydantic schemas for API responses."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class CountryRead(BaseModel):
	"""Representation of a country record."""

	model_config = ConfigDict(from_attributes=True)

	id: int
	name: str
	capital: Optional[str] = None
	region: Optional[str] = None
	population: int
	currency_code: Optional[str] = None
	exchange_rate: Optional[float] = None
	estimated_gdp: Optional[float] = None
	flag_url: Optional[str] = None
	last_refreshed_at: datetime


class StatusResponse(BaseModel):
	"""Status payload for /status endpoint."""

	total_countries: int
	last_refreshed_at: Optional[datetime]
