import requests
import gzip
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

# JioTV APIs
CHANNELS_URL = "https://jiotv.data.cdn.jio.com/apis/v3.0/getMobileChannelList/get/?os=android&devicetype=tv&usertype=tvYR7NSNn7rymo3F"

EPG_URL = "https://jiotv.data.cdn.jio.com/apis/v1.3/getepg/get"

# Example https://jiotv.data.cdn.jio.com/apis/v1.3/getepg/get?channel_id=1104&offset=0&langId=6

# JioTV Images CDN
CHANNEL_LOGO_BASE = "https://jiotv.catchup.cdn.jio.com/dare_images/images/"

# Example https://jiotv.catchup.cdn.jio.com/dare_images/images/History_TV18_SD.png

PROGRAM_IMAGE_BASE = "https://jiotv.catchup.cdn.jio.com/"



HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 12; Smart TV) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
    "Accept": "application/json"
}


def xmltv_time(value):
    """
    Convert JioTV timestamps to XMLTV format.
    """

    if value is None:
        return None

    try:
        value = str(value).strip()

        # Unix timestamp (seconds)
        if value.isdigit() and len(value) == 10:
            return datetime.fromtimestamp(
                int(value)
            ).strftime("%Y%m%d%H%M%S +0530")

        # Unix timestamp (milliseconds)
        if value.isdigit() and len(value) == 13:
            return datetime.fromtimestamp(
                int(value) / 1000
            ).strftime("%Y%m%d%H%M%S +0530")

        # Already XMLTV format
        if value.isdigit() and len(value) == 14:
            return value + " +0530"

        # ISO format
        if "T" in value:
            return datetime.fromisoformat(
                value.replace("Z", "+00:00")
            ).strftime("%Y%m%d%H%M%S +0530")

    except Exception:
        return None

    return None


def fetch_epg(channel, offset=0):
    """
    Download EPG for a single channel.
    """

    session = requests.Session()

    try:
        response = session.get(
            EPG_URL,
            params={
                "channel_id": channel["channel_id"],
                "offset": offset,
                "langId": channel["channelLanguageId"]
            },
            headers=HEADERS,
            timeout=30
        )

        if response.status_code == 200:
            return channel, response.json()

    except Exception:
        pass

    return None


print("Loading channels...")

session = requests.Session()

response = session.get(
    CHANNELS_URL,
    headers=HEADERS,
    timeout=30
)

response.raise_for_status()

channels = response.json()["result"]

print(f"Loaded {len(channels)} channels")

# XMLTV root
tv = ET.Element(
    "tv",
    attrib={
        "generator-info-name": "JioTV XMLTV Generator"
    }
)

# Add channels with logos
for ch in channels:

    channel = ET.SubElement(
        tv,
        "channel",
        id=str(ch["channel_id"])
    )

    ET.SubElement(
        channel,
        "display-name"
    ).text = ch["channel_name"]

    # Channel logo
    if ch.get("logoUrl"):

        ET.SubElement(
            channel,
            "icon",
            src=CHANNEL_LOGO_BASE + ch["logoUrl"]
        )

print("Fetching EPG...")

programme_count = 0

with ThreadPoolExecutor(max_workers=100) as executor:

    futures = [
        executor.submit(fetch_epg, ch, 0)
        for ch in channels
    ]

    for future in as_completed(futures):

        result = future.result()

        if not result:
            continue

        channel, epg = result

        channel_id = str(channel["channel_id"])

        events = []

        if isinstance(epg, dict):

            if isinstance(epg.get("epg"), list):
                events = epg["epg"]

            elif isinstance(epg.get("result"), list):
                events = epg["result"]

            elif isinstance(epg.get("data"), list):
                events = epg["data"]

        for item in events:

            start = (
                item.get("startEpoch")
                or item.get("startTime")
            )

            stop = (
                item.get("endEpoch")
                or item.get("endTime")
            )

            start = xmltv_time(start)
            stop = xmltv_time(stop)

            if not start or not stop:
                continue

            title = (
                item.get("showname")
                or "Unknown"
            )

            desc = (
                item.get("description")
                or item.get("episode_desc")
                or ""
            )

            category = (
                item.get("showCategory")
                or ""
            )

            programme = ET.SubElement(
                tv,
                "programme",
                start=start,
                stop=stop,
                channel=channel_id
            )

            # Title
            ET.SubElement(
                programme,
                "title",
                lang="en"
            ).text = title

            # Description
            if desc:
                ET.SubElement(
                    programme,
                    "desc",
                    lang="en"
                ).text = desc

            # Category
            if category:
                ET.SubElement(
                    programme,
                    "category"
                ).text = category

            # Program image
            image = (
                item.get("episodePoster")
                or item.get("episodeThumbnail")
            )

            if image:
                ET.SubElement(
                    programme,
                    "icon",
                    src=PROGRAM_IMAGE_BASE + image
                )

            # Director
            if item.get("director"):

                credits = ET.SubElement(
                    programme,
                    "credits"
                )

                ET.SubElement(
                    credits,
                    "director"
                ).text = item["director"]

            # Actors
            if item.get("starCast"):

                credits = programme.find("credits")

                if credits is None:
                    credits = ET.SubElement(
                        programme,
                        "credits"
                    )

                for actor in item["starCast"].split(",")[:20]:

                    actor = actor.strip()

                    if actor:
                        ET.SubElement(
                            credits,
                            "actor"
                        ).text = actor

            programme_count += 1

        print(
            f"Fetched: {channel['channel_name']} "
            f"({len(events)} programmes)"
        )

print(f"Total programmes: {programme_count}")

print("Writing epg.xml.gz...")

xml_bytes = ET.tostring(
    tv,
    encoding="utf-8",
    xml_declaration=True
)

with gzip.open(
    "epg.xml.gz",
    "wb",
    compresslevel=9
) as gz:
    gz.write(xml_bytes)

print("Done")
print("Generated:")
print(" - epg.xml.gz")
print(f" - {programme_count} programmes")
