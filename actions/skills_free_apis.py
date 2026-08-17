import os
import json
import logging
import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import requests

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 6. Weather (OpenWeatherMap, WeatherAPI, wttr.in fallback)
# ---------------------------------------------------------------------------

def get_weather_data(city: str) -> str:
    """Fetches real-time weather information for any city/location."""
    clean_city = city.strip()
    
    # 1. OpenWeatherMap if key is present
    owm_key = os.getenv("OPENWEATHERMAP_API_KEY")
    if owm_key:
        try:
            url = f"https://api.openweathermap.org/data/2.5/weather?q={clean_city}&units=metric&appid={owm_key}"
            resp = requests.get(url, timeout=8)
            if resp.status_code == 200:
                data = resp.json()
                temp = data["main"]["temp"]
                feels = data["main"]["feels_like"]
                humidity = data["main"]["humidity"]
                desc = data["weather"][0]["description"].title()
                wind = data["wind"]["speed"]
                name = data["name"]
                country = data["sys"].get("country", "")
                return f"🌤️ **Weather for {name}, {country}:**\n• Condition: {desc}\n• Temperature: {temp}°C (Feels like {feels}°C)\n• Humidity: {humidity}%\n• Wind Speed: {wind} m/s"
        except Exception as e:
            logger.warning(f"OpenWeatherMap error: {e}")

    # 2. WeatherAPI if key is present
    weatherapi_key = os.getenv("WEATHER_API_KEY")
    if weatherapi_key:
        try:
            url = f"https://api.weatherapi.com/v1/current.json?key={weatherapi_key}&q={clean_city}&aqi=no"
            resp = requests.get(url, timeout=8)
            if resp.status_code == 200:
                data = resp.json()
                curr = data["current"]
                loc = data["location"]
                return f"🌤️ **Weather for {loc['name']}, {loc['country']}:**\n• Condition: {curr['condition']['text']}\n• Temperature: {curr['temp_c']}°C (Feels like {curr['feelslike_c']}°C)\n• Humidity: {curr['humidity']}%\n• Wind: {curr['wind_kph']} km/h"
        except Exception as e:
            logger.warning(f"WeatherAPI error: {e}")

    # 3. Fallback to wttr.in JSON (Free, No API Key needed)
    try:
        url = f"https://wttr.in/{clean_city}?format=j1"
        headers = {"User-Agent": "curl/7.68.0"}
        resp = requests.get(url, headers=headers, timeout=8)
        if resp.status_code == 200:
            data = resp.json()
            curr = data["current_condition"][0]
            area = data["nearest_area"][0]["areaName"][0]["value"]
            country = data["nearest_area"][0]["country"][0]["value"]
            desc = curr["weatherDesc"][0]["value"]
            temp_c = curr["temp_C"]
            feels_c = curr["FeelsLikeC"]
            humidity = curr["humidity"]
            wind_km = curr["windspeedKmph"]
            return f"🌤️ **Live Weather for {area}, {country}:**\n• Condition: {desc}\n• Temperature: {temp_c}°C (Feels like {feels_c}°C)\n• Humidity: {humidity}%\n• Wind: {wind_km} km/h"
    except Exception as e:
        logger.warning(f"wttr.in error: {e}")

    return f"❌ Could not retrieve weather data for '{city}'. Please check the city name."


# ---------------------------------------------------------------------------
# 7. News Digest (NewsAPI, GNews, DuckDuckGo News)
# ---------------------------------------------------------------------------

def get_news_digest(topic: Optional[str] = None, country: str = "in", max_items: int = 4) -> str:
    """Fetches top news headlines or topic-specific news."""
    # 1. NewsAPI if key is available
    news_key = os.getenv("NEWSAPI_KEY")
    if news_key:
        try:
            if topic:
                url = f"https://newsapi.org/v2/everything?q={topic}&sortBy=publishedAt&pageSize={max_items}&apiKey={news_key}"
            else:
                url = f"https://newsapi.org/v2/top-headlines?country={country}&pageSize={max_items}&apiKey={news_key}"
            resp = requests.get(url, timeout=8)
            if resp.status_code == 200:
                articles = resp.json().get("articles", [])
                if articles:
                    lines = []
                    for a in articles:
                        src = a.get("source", {}).get("name", "News")
                        title = a.get("title", "")
                        url_link = a.get("url", "#")
                        lines.append(f"📰 [{title}]({url_link})\n   _Source: {src}_")
                    return f"🗞️ **Top News Digest ({topic or country.upper()}):**\n\n" + "\n\n".join(lines)
        except Exception as e:
            logger.warning(f"NewsAPI error: {e}")

    # 2. GNews API if key is available
    gnews_key = os.getenv("GNEWS_API_KEY")
    if gnews_key:
        try:
            q_param = f"q={topic}" if topic else "category=general"
            url = f"https://gnews.io/api/v4/top-headlines?{q_param}&country={country}&max={max_items}&apikey={gnews_key}"
            resp = requests.get(url, timeout=8)
            if resp.status_code == 200:
                articles = resp.json().get("articles", [])
                if articles:
                    lines = [f"📰 [{a.get('title')}]({a.get('url')})\n   _{a.get('description')}_" for a in articles]
                    return f"🗞️ **News Headlines:**\n\n" + "\n\n".join(lines)
        except Exception as e:
            logger.warning(f"GNews error: {e}")

    # 3. DuckDuckGo / DDGS News Fallback (Free, zero key)
    try:
        try:
            from ddgs import DDGS
        except ImportError:
            from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.news(topic or "world news top headlines", max_results=max_items))
            if results:
                lines = []
                for r in results:
                    lines.append(f"📰 [{r.get('title')}]({r.get('url')})\n   _{r.get('source', 'News')}: {r.get('body', '')[:120]}..._")
                return f"🗞️ **Latest News ({topic or 'Top Headlines'}):**\n\n" + "\n\n".join(lines)
    except Exception as e:
        logger.warning(f"DDG news error: {e}")

    return "❌ Unable to fetch news right now. Please try again in a moment."


# ---------------------------------------------------------------------------
# 8. Currency Exchange Rates (ExchangeRate-API)
# ---------------------------------------------------------------------------

def get_currency_conversion(amount: float, from_curr: str, to_curr: str) -> str:
    """Converts amount between currencies using real-time rates."""
    from_c = from_curr.upper().strip()
    to_c = to_curr.upper().strip()
    key = os.getenv("EXCHANGERATE_API_KEY", "")
    
    try:
        if key:
            url = f"https://v6.exchangerate-api.com/v6/{key}/pair/{from_c}/{to_c}/{amount}"
            resp = requests.get(url, timeout=8)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("result") == "success":
                    converted = data.get("conversion_result", amount)
                    rate = data.get("conversion_rate", 1.0)
                    date_updated = data.get("time_last_update_utc", "")[:16]
                    return f"💱 **Currency Exchange:**\n`{amount:,.2f} {from_c}` = **`{converted:,.2f} {to_c}`**\n• Exchange Rate: `1 {from_c} = {rate:.4f} {to_c}`\n• Updated: {date_updated}"
        
        # Free open exchange rate API fallback
        url = f"https://open.er-api.com/v6/latest/{from_c}"
        resp = requests.get(url, timeout=8)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("result") == "success":
                rates = data.get("rates", {})
                if to_c in rates:
                    rate = rates[to_c]
                    converted = amount * rate
                    date_updated = data.get("time_last_update_utc", "")[:16]
                    return f"💱 **Currency Exchange:**\n`{amount:,.2f} {from_c}` = **`{converted:,.2f} {to_c}`**\n• Exchange Rate: `1 {from_c} = {rate:.4f} {to_c}`\n• Updated: {date_updated}"
                else:
                    return f"❌ Target currency `{to_c}` not found in exchange rate database."
            else:
                return f"❌ Base currency `{from_c}` not supported."
    except Exception as e:
        logger.warning(f"Currency API error: {e}")

    return f"❌ Failed to convert {amount} {from_c} to {to_c}."


# ---------------------------------------------------------------------------
# 9. Crypto & Blockchain Prices (CoinGecko & Etherscan)
# ---------------------------------------------------------------------------

def get_crypto_price(coins: str = "bitcoin,ethereum,solana,dogecoin") -> str:
    """Fetches real-time cryptocurrency prices from CoinGecko."""
    try:
        coin_ids = ",".join([c.strip().lower() for c in coins.split(",")])
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_ids}&vs_currencies=usd,inr&include_24hr_change=true"
        resp = requests.get(url, timeout=8)
        if resp.status_code == 200:
            data = resp.json()
            if not data:
                return f"🪙 No crypto data found for `{coins}`."

            lines = []
            for coin, val in data.items():
                usd = val.get("usd", 0)
                inr = val.get("inr", 0)
                change = val.get("usd_24h_change", 0.0)
                icon = "🟢" if change >= 0 else "🔴"
                lines.append(f"• **{coin.title()}**: `${usd:,.2f}` | `₹{inr:,.2f}` ({icon} {change:+.2f}% 24h)")

            return "🪙 **Live Crypto Prices (CoinGecko):**\n\n" + "\n".join(lines)
    except Exception as e:
        logger.warning(f"CoinGecko error: {e}")

    return f"❌ Failed to fetch crypto prices for {coins}."


def get_etherscan_gas_price() -> str:
    """Fetches Ethereum gas prices and chain statistics via Etherscan V2."""
    key = os.getenv("ETHERSCAN_API_KEY", "")
    if not key:
        return "⚠️ Etherscan API key not set in `.env` (`ETHERSCAN_API_KEY`)."
    try:
        url = f"https://api.etherscan.io/v2/api?chainid=1&module=gastracker&action=gasoracle&apikey={key}"
        resp = requests.get(url, timeout=8)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("status") == "1":
                r = data.get("result", {})
                return (
                    f"⛽ **Ethereum Gas Tracker (Etherscan):**\n"
                    f"• Safe / Low: `{r.get('SafeGasPrice')} Gwei`\n"
                    f"• Proposed / Standard: `{r.get('ProposeGasPrice')} Gwei`\n"
                    f"• Fast: `{r.get('FastGasPrice')} Gwei`\n"
                    f"• Base Fee: `{r.get('suggestBaseFee', 'N/A')} Gwei`\n"
                    f"• Last Block: `{r.get('LastBlock', 'N/A')}`"
                )
    except Exception as e:
        logger.warning(f"Etherscan error: {e}")

    return "❌ Failed to fetch Etherscan gas data."


# ---------------------------------------------------------------------------
# 10. Books & Wikipedia Lookup (OpenLibrary & Wikipedia API)
# ---------------------------------------------------------------------------

def lookup_book_openlibrary(query: str) -> str:
    """Searches OpenLibrary for book information."""
    try:
        url = f"https://openlibrary.org/search.json?q={requests.utils.quote(query)}&limit=3"
        resp = requests.get(url, timeout=8)
        if resp.status_code == 200:
            docs = resp.json().get("docs", [])
            if not docs:
                return f"📚 No books found matching '{query}' on OpenLibrary."

            lines = []
            for b in docs:
                title = b.get("title", "Unknown Title")
                authors = ", ".join(b.get("author_name", ["Unknown Author"]))
                year = b.get("first_publish_year", "N/A")
                ratings = b.get("ratings_average", "N/A")
                if isinstance(ratings, float):
                    ratings = f"{ratings:.1f}⭐"
                key = b.get("key", "")
                link = f"https://openlibrary.org{key}" if key else ""
                lines.append(f"📖 **[{title}]({link})**\n• Author: {authors}\n• First Published: {year}\n• Rating: {ratings}")

            return f"📚 **Book Search Results for '{query}':**\n\n" + "\n\n".join(lines)
    except Exception as e:
        logger.warning(f"OpenLibrary error: {e}")

    return f"❌ Failed to look up book '{query}'."


def lookup_wikipedia(query: str) -> str:
    """Searches Wikipedia API for instant factual summary."""
    try:
        clean_q = query.strip().replace(" ", "_")
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{requests.utils.quote(clean_q)}"
        headers = {"User-Agent": "AlyaBot/1.0 (https://t.me/Alya_Rasa_Bot)"}
        resp = requests.get(url, headers=headers, timeout=8)
        if resp.status_code == 200:
            data = resp.json()
            title = data.get("title", query)
            extract = data.get("extract", "No summary available.")
            page_url = data.get("content_urls", {}).get("desktop", {}).get("page", "")
            img_url = data.get("thumbnail", {}).get("source", "")
            res = f"🌐 **Wikipedia: [{title}]({page_url})**\n\n{extract}"
            return res
        else:
            return f"🌐 No direct Wikipedia article found for '{query}'."
    except Exception as e:
        logger.warning(f"Wikipedia lookup error: {e}")

    return f"❌ Wikipedia lookup failed for '{query}'."


# ---------------------------------------------------------------------------
# 11. Movies & TV Info (OMDb, TMDB, TVMaze)
# ---------------------------------------------------------------------------

def get_movie_info(title: str) -> str:
    """Fetches movie/show details using OMDb, TMDB, or TVMaze."""
    # 1. OMDb API if key is available
    omdb_key = os.getenv("OMDB_API_KEY")
    if omdb_key:
        try:
            url = f"https://www.omdbapi.com/?t={requests.utils.quote(title)}&apikey={omdb_key}"
            resp = requests.get(url, timeout=8)
            if resp.status_code == 200:
                d = resp.json()
                if d.get("Response") == "True":
                    return (
                        f"🎬 **{d.get('Title')} ({d.get('Year')})**\n"
                        f"• Genre: {d.get('Genre')} | Runtime: {d.get('Runtime')}\n"
                        f"• IMDb Rating: ⭐ `{d.get('imdbRating')}/10` (Votes: {d.get('imdbVotes')})\n"
                        f"• Director: {d.get('Director')}\n"
                        f"• Actors: {d.get('Actors')}\n"
                        f"• Plot: _{d.get('Plot')}_"
                    )
        except Exception as e:
            logger.warning(f"OMDb error: {e}")

    # 2. TVMaze Free API (Zero API key fallback for shows)
    try:
        url = f"https://api.tvmaze.com/singlesearch/shows?q={requests.utils.quote(title)}"
        resp = requests.get(url, timeout=8)
        if resp.status_code == 200:
            d = resp.json()
            name = d.get("name")
            genres = ", ".join(d.get("genres", []))
            rating = d.get("rating", {}).get("average", "N/A")
            summary = d.get("summary", "").replace("<p>", "").replace("</p>", "").replace("<b>", "").replace("</b>", "")
            premiered = d.get("premiered", "N/A")
            return f"🎬 **{name} ({premiered[:4]})**\n• Genres: {genres}\n• Rating: ⭐ `{rating}/10`\n• Status: {d.get('status')}\n• Summary: _{summary}_"
    except Exception as e:
        logger.warning(f"TVMaze error: {e}")

    return f"❌ Could not find movie/TV show details for '{title}'."


# ---------------------------------------------------------------------------
# 12. Holidays & Festivals (Calendarific / Nager.Date)
# ---------------------------------------------------------------------------

def get_upcoming_holidays(country_code: str = "IN", year: Optional[int] = None) -> str:
    """Fetches public holidays and festivals."""
    if not year:
        year = datetime.now().year

    # 1. Calendarific if key is available
    cal_key = os.getenv("CALENDARIFIC_API_KEY")
    if cal_key:
        try:
            url = f"https://calendarific.com/api/v2/holidays?api_key={cal_key}&country={country_code}&year={year}"
            resp = requests.get(url, timeout=8)
            if resp.status_code == 200:
                hols = resp.json().get("response", {}).get("holidays", [])
                if hols:
                    lines = [f"🎉 **{h.get('name')}** — `{h.get('date', {}).get('iso')}` ({h.get('primary_type')})" for h in hols[:6]]
                    return f"🗓️ **Public Holidays ({country_code.upper()} - {year}):**\n\n" + "\n".join(lines)
        except Exception as e:
            logger.warning(f"Calendarific error: {e}")

    # 2. Nager.Date free global holidays API (No key needed)
    try:
        url = f"https://date.nager.at/api/v3/PublicHolidays/{year}/{country_code.upper()}"
        resp = requests.get(url, timeout=8)
        if resp.status_code == 200:
            hols = resp.json()
            today_str = datetime.now().strftime("%Y-%m-%d")
            upcoming = [h for h in hols if h.get("date") >= today_str][:6]
            if not upcoming:
                upcoming = hols[:6]

            lines = [f"🎉 **{h.get('localName')} / {h.get('name')}**\n• Date: `{h.get('date')}`" for h in upcoming]
            return f"🗓️ **Upcoming Holidays ({country_code.upper()} - {year}):**\n\n" + "\n\n".join(lines)
    except Exception as e:
        logger.warning(f"Nager.Date error: {e}")

    return f"❌ Failed to fetch holidays for country `{country_code}`."


# ---------------------------------------------------------------------------
# 13. Images (Unsplash & Pexels)
# ---------------------------------------------------------------------------

def search_stock_images(query: str, max_results: int = 3) -> str:
    """Searches stock images from Unsplash or Pexels."""
    # 1. Unsplash if key is present
    unsplash_key = os.getenv("UNSPLASH_ACCESS_KEY")
    if unsplash_key:
        try:
            url = f"https://api.unsplash.com/search/photos?query={requests.utils.quote(query)}&per_page={max_results}&client_id={unsplash_key}"
            resp = requests.get(url, timeout=8)
            if resp.status_code == 200:
                photos = resp.json().get("results", [])
                if photos:
                    lines = []
                    for p in photos:
                        desc = p.get("alt_description") or query
                        user = p.get("user", {}).get("name", "Photographer")
                        urls = p.get("urls", {}).get("regular", "")
                        lines.append(f"📸 **[{desc.title()}]({urls})** (Photo by {user})")
                    return f"🖼️ **Unsplash Images for '{query}':**\n\n" + "\n\n".join(lines)
        except Exception as e:
            logger.warning(f"Unsplash error: {e}")

    # 2. Pexels if key is present
    pexels_key = os.getenv("PEXELS_API_KEY")
    if pexels_key:
        try:
            headers = {"Authorization": pexels_key}
            url = f"https://api.pexels.com/v1/search?query={requests.utils.quote(query)}&per_page={max_results}"
            resp = requests.get(url, headers=headers, timeout=8)
            if resp.status_code == 200:
                photos = resp.json().get("photos", [])
                lines = [f"📸 **[{p.get('alt', query)}]({p.get('src', {}).get('large')})** (Photo by {p.get('photographer')})" for p in photos]
                return f"🖼️ **Pexels Images for '{query}':**\n\n" + "\n\n".join(lines)
        except Exception as e:
            logger.warning(f"Pexels error: {e}")

    return f"🖼️ Check Unsplash directly for high-res images: https://unsplash.com/s/photos/{requests.utils.quote(query)}"


# ---------------------------------------------------------------------------
# 14. Dictionary & Translation (Free Dictionary & MyMemory API)
# ---------------------------------------------------------------------------

def lookup_dictionary(word: str) -> str:
    """Fetches word definition, phonetics, and examples from Free Dictionary API."""
    try:
        url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{requests.utils.quote(word.strip())}"
        resp = requests.get(url, timeout=8)
        if resp.status_code == 200:
            data = resp.json()[0]
            phonetic = data.get("phonetic", "")
            meanings = data.get("meanings", [])

            lines = [f"📖 **Word: `{data.get('word')}`** {f'({phonetic})' if phonetic else ''}"]
            for m in meanings[:2]:
                pos = m.get("partOfSpeech", "meaning")
                defs = m.get("definitions", [])[:2]
                lines.append(f"\n*_{pos.title()}_*:")
                for d in defs:
                    ex = f"\n  _Example: \"{d.get('example')}\"_" if d.get("example") else ""
                    lines.append(f"• {d.get('definition')}{ex}")

            return "\n".join(lines)
    except Exception as e:
        logger.warning(f"Dictionary error: {e}")

    return f"❌ No dictionary entry found for '{word}'."


def translate_text(text: str, source_lang: str = "en", target_lang: str = "hi") -> str:
    """Translates text using MyMemory Free Translation API."""
    try:
        url = f"https://api.mymemory.translated.net/get?q={requests.utils.quote(text)}&langpair={source_lang}|{target_lang}"
        resp = requests.get(url, timeout=8)
        if resp.status_code == 200:
            translated = resp.json().get("responseData", {}).get("translatedText")
            if translated:
                return f"🌐 **Translation ({source_lang.upper()} ➔ {target_lang.upper()}):**\n\n`{translated}`"
    except Exception as e:
        logger.warning(f"Translation API error: {e}")

    return f"❌ Translation failed for text."


# ---------------------------------------------------------------------------
# 15. Jokes & Quotes (JokeAPI, ZenQuotes)
# ---------------------------------------------------------------------------

def get_random_joke() -> str:
    """Fetches a clean joke from JokeAPI."""
    try:
        url = "https://v2.jokeapi.dev/joke/Any?blacklistFlags=nsfw,religious,political,racist,sexist,explicit"
        resp = requests.get(url, timeout=8)
        if resp.status_code == 200:
            d = resp.json()
            if d.get("type") == "single":
                return f"😂 **Joke Time:**\n\n{d.get('joke')}"
            else:
                return f"😂 **Joke Time:**\n\n{d.get('setup')}\n\n👉 {d.get('delivery')}"
    except Exception as e:
        logger.warning(f"JokeAPI error: {e}")

    return "😂 *Why don't scientists trust atoms? Because they make up everything!*"


def get_random_quote() -> str:
    """Fetches an inspirational quote from ZenQuotes."""
    try:
        url = "https://zenquotes.io/api/random"
        resp = requests.get(url, timeout=8)
        if resp.status_code == 200:
            data = resp.json()[0]
            return f"✨ **Quote of the Moment:**\n\n_\"{data.get('q')}\"_\n\n— **{data.get('a')}**"
    except Exception as e:
        logger.warning(f"ZenQuotes error: {e}")

    return "✨ *\"The secret of getting ahead is getting started.\"* — Mark Twain"


# ---------------------------------------------------------------------------
# 16. Vehicle Info Lookup (NHTSA Free VIN API)
# ---------------------------------------------------------------------------

def lookup_vehicle_vin(vin: str) -> str:
    """Decodes a Vehicle Identification Number (VIN) using NHTSA API."""
    try:
        clean_vin = vin.strip().upper()
        url = f"https://vpic.nhtsa.dot.gov/api/vehicles/decodevin/{clean_vin}?format=json"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            results = resp.json().get("Results", [])
            details = {item.get("Variable"): item.get("Value") for item in results if item.get("Value")}

            make = details.get("Make", "N/A")
            model = details.get("Model", "N/A")
            year = details.get("Model Year", "N/A")
            v_type = details.get("Vehicle Type", "N/A")
            body = details.get("Body Class", "N/A")
            mfg = details.get("Manufacturer Name", "N/A")
            engine = details.get("Displacement (L)", details.get("Displacement (CC)", "N/A"))

            return (
                f"🚗 **Vehicle Details (VIN: `{clean_vin}`):**\n\n"
                f"• Make & Model: **{year} {make} {model}**\n"
                f"• Vehicle Type: `{v_type}` ({body})\n"
                f"• Manufacturer: {mfg}\n"
                f"• Engine / Displacement: {engine}\n"
                f"• Fuel Type: {details.get('Fuel Type - Primary', 'N/A')}\n"
                f"• Plant Country: {details.get('Plant Country', 'N/A')}"
            )
    except Exception as e:
        logger.warning(f"VIN lookup error: {e}")

    return f"❌ Failed to decode VIN `{vin}`."


# ---------------------------------------------------------------------------
# 17. Shopping & Price Comparison (OpenFoodFacts / FakeStore)
# ---------------------------------------------------------------------------

def lookup_product_info(barcode_or_name: str) -> str:
    """Looks up product details and ingredients via OpenFoodFacts / product database."""
    clean = barcode_or_name.strip()
    if clean.isdigit():
        try:
            url = f"https://world.openfoodfacts.org/api/v0/product/{clean}.json"
            resp = requests.get(url, timeout=8)
            if resp.status_code == 200:
                p = resp.json().get("product", {})
                name = p.get("product_name", "Unknown Product")
                brands = p.get("brands", "N/A")
                nutri = p.get("nutrition_grades", "N/A").upper()
                return f"🛒 **Product Found:**\n• Name: **{name}**\n• Brand: {brands}\n• Nutri-Score: `{nutri}`\n• Category: {p.get('categories', 'N/A')[:60]}"
        except Exception as e:
            logger.warning(f"OpenFoodFacts error: {e}")

    # Fallback to search query
    return f"🛒 **Shopping Comparison for '{clean}':**\n• Amazon: https://www.amazon.in/s?k={requests.utils.quote(clean)}\n• Flipkart: https://www.flipkart.com/search?q={requests.utils.quote(clean)}"


# ---------------------------------------------------------------------------
# 18. Security & Threat Intelligence (XposedOrNot & HaveIBeenPwned)
# ---------------------------------------------------------------------------

def check_email_breach(email: str) -> str:
    """Checks if an email address has been exposed in data breaches via XposedOrNot API."""
    clean_email = email.strip().lower()
    try:
        url = f"https://api.xposedornot.com/v1/check-email/{requests.utils.quote(clean_email)}"
        headers = {"User-Agent": "Alya-Security-Bot/1.0"}
        resp = requests.get(url, headers=headers, timeout=8)
        
        if resp.status_code == 200:
            data = resp.json()
            raw_breaches = data.get("breaches", [])
            # XposedOrNot returns breaches as a list of lists or list of strings
            breach_list = []
            if raw_breaches:
                if isinstance(raw_breaches[0], list):
                    breach_list = raw_breaches[0]
                else:
                    breach_list = raw_breaches

            if breach_list:
                count = len(breach_list)
                preview = ", ".join(breach_list[:8])
                more = f" and {count - 8} more" if count > 8 else ""
                return (
                    f"🚨 **Security Alert for `{clean_email}`:**\n"
                    f"This email address was found exposed in **{count} data breaches**!\n\n"
                    f"• **Exposed in:** {preview}{more}\n"
                    f"• **Recommendation:** Change passwords on affected accounts immediately and enable 2-Factor Authentication (2FA)."
                )

        if resp.status_code == 404 or "Error" in resp.text:
            return f"✅ **Good News:** `{clean_email}` was **NOT found** in any known public data breaches!"

    except Exception as e:
        logger.warning(f"XposedOrNot error: {e}")

    return f"❌ Unable to verify email breach status for `{clean_email}` right now."


def check_password_breach(password: str) -> str:
    """Checks if a password has appeared in data breaches using HIBP k-Anonymity API."""
    try:
        sha1_pwd = hashlib.sha1(password.encode("utf-8")).hexdigest().upper()
        prefix = sha1_pwd[:5]
        suffix = sha1_pwd[5:]

        url = f"https://api.pwnedpasswords.com/range/{prefix}"
        headers = {"User-Agent": "Alya-Security-Bot/1.0"}
        resp = requests.get(url, headers=headers, timeout=8)
        if resp.status_code == 200:
            for line in resp.text.splitlines():
                parts = line.split(":")
                if parts[0] == suffix:
                    count = int(parts[1])
                    return f"🚨 **Security Alert:** This password has appeared in **{count:,}** data breaches! You should NOT use it."
            return "✅ **Good News:** This password was NOT found in known public data breaches."
    except Exception as e:
        logger.warning(f"HIBP error: {e}")

    return "❌ Security breach check unavailable."


def check_security_breach(query: str) -> str:
    """Automatically checks email address or password for exposure in data breaches."""
    clean = query.strip()
    if "@" in clean and "." in clean:
        return check_email_breach(clean)
    return check_password_breach(clean)


def check_ip_or_domain_threat(target: str) -> str:
    """Performs threat intelligence reputation check on an IP or domain."""
    clean_target = target.strip()
    return f"🛡️ **Threat Reputation for `{clean_target}`:**\n• VirusTotal: https://www.virustotal.com/gui/search/{requests.utils.quote(clean_target)}\n• AbuseIPDB: https://www.abuseipdb.com/check/{requests.utils.quote(clean_target)}\n• Status: Clean check recommended prior to interacting with unknown endpoints."


# ---------------------------------------------------------------------------
# 19. Math & NASA Science API (Sympy CAS & NASA APOD)
# ---------------------------------------------------------------------------

def solve_math_expression(expression: str) -> str:
    """Solves algebraic, calculus, scientific, and arithmetic problems with WolframAlpha and SymPy."""
    wolfram_id = os.getenv("WOLFRAM_APP_ID", "")
    if wolfram_id:
        for endpoint in ["result", "spoken"]:
            try:
                url = f"https://api.wolframalpha.com/v1/{endpoint}?i={requests.utils.quote(expression)}&appid={wolfram_id}"
                resp = requests.get(url, timeout=10)
                if resp.status_code == 200 and resp.text and not resp.text.startswith("No short answer"):
                    return f"🧠 **WolframAlpha Answer:**\n`{expression}`\n\n👉 **{resp.text}**"
            except Exception as e:
                logger.warning(f"WolframAlpha {endpoint} error: {e}")

    try:
        import sympy as sp
        clean_expr = expression.replace("^", "**").replace("=", " - ")
        
        # Check if equation with variable
        if any(c in clean_expr for c in ["x", "y", "z"]):
            x = sp.Symbol('x')
            try:
                parsed = sp.sympify(clean_expr)
                roots = sp.solve(parsed, x)
                simplified = sp.simplify(parsed)
                return f"🔢 **Math Solver (SymPy):**\n• Simplified Expression: `{sp.pretty(simplified)}`\n• Solutions for x: `{roots}`"
            except Exception:
                pass

        result = sp.sympify(clean_expr).evalf()
        return f"🔢 **Math Calculation:**\n`{expression}` = **`{result}`**"
    except Exception as e:
        return f"❌ Failed to solve math expression '{expression}': {str(e)}"


def get_nasa_apod() -> str:
    """Fetches NASA Astronomy Picture of the Day (APOD)."""
    nasa_key = os.getenv("NASA_API_KEY", "DEMO_KEY")
    try:
        url = f"https://api.nasa.gov/planetary/apod?api_key={nasa_key}"
        resp = requests.get(url, timeout=8)
        if resp.status_code == 200:
            data = resp.json()
            title = data.get("title")
            explanation = data.get("explanation", "")
            img_url = data.get("hdurl") or data.get("url")
            date_str = data.get("date")
            return f"🚀 **NASA Astronomy Picture of the Day ({date_str}):**\n\n🪐 **[{title}]({img_url})**\n\n_{explanation[:400]}..._\n\n🔗 View Image: {img_url}"
    except Exception as e:
        logger.warning(f"NASA APOD error: {e}")

    return "❌ Failed to fetch NASA APOD."
