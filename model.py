#!/usr/bin/python3
"""Country database model."""

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class Country(SQLModel, table=True):
	"""Persisted country entry."""

	id: Optional[int] = Field(default=None, primary_key=True)
	name: str = Field(nullable=False, index=True)
	capital: Optional[str] = Field(default=None)
	region: Optional[str] = Field(default=None, index=True)
	population: int = Field(nullable=False)
	currency_code: Optional[str] = Field(default=None, index=True)
	exchange_rate: Optional[float] = Field(default=None)
	estimated_gdp: Optional[float] = Field(default=None)
	flag_url: Optional[str] = Field(default=None)
	last_refreshed_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

	def update_from_refresh(
		self,
		*,
		capital: Optional[str],
		region: Optional[str],
		population: int,
		currency_code: Optional[str],
		exchange_rate: Optional[float],
		estimated_gdp: Optional[float],
		flag_url: Optional[str],
		refresh_time: datetime,
	) -> None:
		"""Update fields during a refresh."""
		self.capital = capital
		self.region = region
		self.population = population
		self.currency_code = currency_code
		self.exchange_rate = exchange_rate
		self.estimated_gdp = estimated_gdp
		self.flag_url = flag_url
		self.last_refreshed_at = refresh_time
