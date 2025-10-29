from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from sqlalchemy import func
from sqlmodel import Session, select

from model import Country


CACHE_DIR = Path(__file__).resolve().parent / "cache"
SUMMARY_PATH = CACHE_DIR / "summary.png"
IMAGE_SIZE = (600, 320)
BACKGROUND = "white"
FOREGROUND = "black"


def generate_image(session: Session, last_refreshed_at: datetime) -> Path:
	"""Create a summary image with total count, top GDP countries, and timestamp."""
	CACHE_DIR.mkdir(parents=True, exist_ok=True)

	total_result = session.exec(select(func.count()).select_from(Country)).first()
	total_count = total_result[0] if isinstance(total_result, tuple) else (total_result or 0)

	top_countries = session.exec(
		select(Country)
		.where(Country.estimated_gdp.isnot(None))
		.order_by(Country.estimated_gdp.desc())
		.limit(5)
	).all()

	image = Image.new("RGB", IMAGE_SIZE, BACKGROUND)
	draw = ImageDraw.Draw(image)
	font = ImageFont.load_default()

	lines = [
		f"Total countries: {total_count}",
		f"Last refreshed at: {last_refreshed_at.isoformat()}",
		"Top 5 countries by estimated GDP:",
	]

	if top_countries:
		for index, country in enumerate(top_countries, start=1):
			value = f"{country.estimated_gdp:,.2f}" if country.estimated_gdp is not None else "N/A"
			lines.append(f"{index}. {country.name} — {value}")
	else:
		lines.append("No GDP data available yet.")

	y = 20
	for line in lines:
		draw.text((20, y), line, font=font, fill=FOREGROUND)
		y += 40

	image.save(SUMMARY_PATH)
	return SUMMARY_PATH
