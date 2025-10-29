from datetime import datetime
from random import randint
from typing import Any, Optional

import requests
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from requests import RequestException
from sqlalchemy import func, nullsfirst, nullslast
from sqlalchemy.sql import Select
from sqlmodel import Session, select


from db import get_session, init_db
from model import Country
from schema import CountryRead, StatusResponse
from utils import SUMMARY_PATH, generate_image


COUNTRIES_URL = "https://restcountries.com/v2/all?fields=name,capital,region,population,flag,currencies"
EXCHANGE_RATES_URL = "https://open.er-api.com/v6/latest/USD"


load_dotenv()
init_db()

app = FastAPI()

app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"],
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)


def _error(status_code: int, error: str, details: Optional[Any] = None) -> HTTPException:
	body = {"error": error}
	if details:
		body["details"] = details
	return HTTPException(status_code=status_code, detail=body)


def _apply_filters(statement: Select, region: Optional[str], currency: Optional[str]) -> Select:
	if region:
		statement = statement.where(func.lower(Country.region) == region.lower())
	if currency:
		statement = statement.where(func.lower(Country.currency_code) == currency.lower())
	return statement


def _apply_sort(statement: Select, sort: Optional[str]) -> Select:
	if not sort:
		return statement

	sort_key = sort.lower()
	if sort_key == "gdp_desc":
		return statement.order_by(nullslast(Country.estimated_gdp.desc()))
	if sort_key == "gdp_asc":
		return statement.order_by(nullsfirst(Country.estimated_gdp.asc()))

	raise _error(
		status.HTTP_400_BAD_REQUEST,
		"Validation failed",
		{"sort": "Unsupported sort value. Use gdp_desc or gdp_asc."},
	)


def _scalar(result: Any, default: int = 0) -> int:
	if isinstance(result, tuple):
		return result[0]
	return result if result is not None else default


@app.get("/countries", response_model=list[CountryRead])
def list_countries(
	region: Optional[str] = Query(default=None, description="Filter by region"),
	currency: Optional[str] = Query(default=None, description="Filter by currency code"),
	sort: Optional[str] = Query(default=None, description="Sort by GDP: gdp_desc|gdp_asc"),
	session: Session = Depends(get_session),
) -> list[CountryRead]:
	statement = select(Country)
	statement = _apply_filters(statement, region, currency)
	statement = _apply_sort(statement, sort)

	countries = session.exec(statement).all()
	return countries


def _fetch_json(url: str, source_name: str) -> Any:
	try:
		response = requests.get(url, timeout=20)
		response.raise_for_status()
		return response.json()
	except RequestException as exc:
		raise _error(
			status.HTTP_503_SERVICE_UNAVAILABLE,
			"External data source unavailable",
			f"Could not fetch data from {source_name}",
		) from exc


@app.post("/countries/refresh")
def refresh_countries(session: Session = Depends(get_session)) -> dict:
	countries_data = _fetch_json(COUNTRIES_URL, "REST Countries API")
	exchange_data = _fetch_json(EXCHANGE_RATES_URL, "Open Exchange Rates API")

	if not isinstance(countries_data, list):
		raise _error(status.HTTP_503_SERVICE_UNAVAILABLE, "External data source unavailable")

	exchange_rates = exchange_data.get("rates", {})
	refresh_time = datetime.utcnow()

	existing_countries = {
		country.name.lower(): country for country in session.exec(select(Country)).all()
	}

	created = 0
	updated = 0

	for entry in countries_data:
		name = entry.get("name")
		population = entry.get("population")

		if not name:
			raise _error(
				status.HTTP_400_BAD_REQUEST,
				"Validation failed",
				{"name": "is required"},
			)
		if population is None:
			raise _error(
				status.HTTP_400_BAD_REQUEST,
				"Validation failed",
				{"population": f"is required for {name}"},
			)

		currencies = entry.get("currencies") or []
		currency_code = None
		exchange_rate = None
		estimated_gdp: Optional[float] = None

		if currencies:
			currency_code = (currencies[0] or {}).get("code")
			currency_code = currency_code.upper() if currency_code else None

		if currency_code:
			exchange_rate = exchange_rates.get(currency_code)
			if exchange_rate:
				exchange_rate = float(exchange_rate)
				if exchange_rate != 0:
					multiplier = randint(1000, 2000)
					estimated_gdp = (population * multiplier) / exchange_rate
				else:
					estimated_gdp = None
			else:
				exchange_rate = None
				estimated_gdp = None
		else:
			estimated_gdp = 0

		capital = entry.get("capital")
		region = entry.get("region")
		flag_url = entry.get("flag")

		lower_name = name.lower()
		country = existing_countries.get(lower_name)

		if country:
			country.update_from_refresh(
				capital=capital,
				region=region,
				population=population,
				currency_code=currency_code,
				exchange_rate=exchange_rate,
				estimated_gdp=estimated_gdp,
				flag_url=flag_url,
				refresh_time=refresh_time,
			)
			updated += 1
		else:
			country = Country(
				name=name,
				capital=capital,
				region=region,
				population=population,
				currency_code=currency_code,
				exchange_rate=exchange_rate,
				estimated_gdp=estimated_gdp,
				flag_url=flag_url,
				last_refreshed_at=refresh_time,
			)
			session.add(country)
			created += 1
			existing_countries[lower_name] = country

	try:
		session.flush()
		generate_image(session, refresh_time)
	except Exception as exc:
		session.rollback()
		print(exc)
		raise _error(
			status.HTTP_500_INTERNAL_SERVER_ERROR,
			"Internal server error",
			"Failed to generate summary image",
		) from exc

	try:
		session.commit()
	except Exception as exc:
		session.rollback()
		raise _error(status.HTTP_500_INTERNAL_SERVER_ERROR, "Internal server error") from exc

	total_result = session.exec(select(func.count()).select_from(Country)).first()
	total = _scalar(total_result)
	return {
		"message": "Refresh complete",
		"created": created,
		"updated": updated,
		"total_countries": total,
		"last_refreshed_at": refresh_time.isoformat(),
	}


@app.get("/countries/image")
def get_country_image():
	if not SUMMARY_PATH.exists():
		raise _error(status.HTTP_404_NOT_FOUND, "Summary image not found")
	return FileResponse(SUMMARY_PATH)


@app.get("/countries/{name}", response_model=CountryRead)
def get_country(name: str, session: Session = Depends(get_session)) -> CountryRead:
	statement = select(Country).where(func.lower(Country.name) == name.lower())
	country = session.exec(statement).first()
	if not country:
		raise _error(status.HTTP_404_NOT_FOUND, "Country not found")
	return country


@app.delete("/countries/{name}")
def delete_country(name: str, session: Session = Depends(get_session)) -> dict:
	statement = select(Country).where(func.lower(Country.name) == name.lower())
	country = session.exec(statement).first()
	if not country:
		raise _error(status.HTTP_404_NOT_FOUND, "Country not found")

	session.delete(country)
	session.commit()
	return {"message": "Country deleted successfully"}


@app.get("/status", response_model=StatusResponse)
def get_status(session: Session = Depends(get_session)) -> StatusResponse:
	total_result = session.exec(select(func.count()).select_from(Country)).first()
	total_countries = _scalar(total_result)
	last_country = session.exec(
		select(Country).order_by(Country.last_refreshed_at.desc())
	).first()
	last_refreshed_at = last_country.last_refreshed_at if last_country else None
	return StatusResponse(total_countries=total_countries, last_refreshed_at=last_refreshed_at)
