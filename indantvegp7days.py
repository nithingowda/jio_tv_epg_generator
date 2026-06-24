from requests import Session
from requests.adapters import HTTPAdapter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from xml.sax.saxutils import escape
import gzip

CHANNELS_URL = "https://jiotv.data.cdn.jio.com/apis/v3.0/getMobileChannelList/get/?os=android&devicetype=tv&usertype=tvYR7NSNn7rymo3F"
EPG_URL = "https://jiotv.data.cdn.jio.com/apis/v1.3/getepg/get"

CHANNEL_LOGO_BASE = "https://jiotv.catchup.cdn.jio.com/dare_images/images/"
PROGRAM_IMAGE_BASE = "https://jiotv.catchup.cdn.jio.com/"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 12; Smart TV) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
    "Accept": "application/json"
}

session = Session()

adapter = HTTPAdapter(
    pool_connections=200,
    pool_maxsize=200
)

session.mount("http://", adapter)
session.mount("https://", adapter)


def xmltv_time(value):
    if value is None:
        return None

    try:
        value = str(value)

        if value.isdigit() and len(value) == 13:
            return datetime.fromtimestamp(
                int(value) / 1000
            ).strftime("%Y%m%d%H%M%S +0530")

        if value.isdigit() and len(value) == 10:
            return datetime.fromtimestamp(
                int(value)
            ).strftime("%Y%m%d%H%M%S +0530")

        if value.isdigit() and len(value) == 14:
            return value + " +0530"

    except Exception:
        pass

    return None


def fetch_epg(channel):
    all_events = []

    for day in range(7):
        try:
            r = session.get(
                EPG_URL,
                params={
                    "channel_id": channel["channel_id"],
                    "offset": day,
                    "langId": channel["channelLanguageId"]
                },
                headers=HEADERS,
                timeout=20
            )

            if not r.ok:
                continue

            data = r.json()

            events = []

            if isinstance(data, dict):

                if isinstance(data.get("epg"), list):
                    events = data["epg"]

                elif isinstance(data.get("result"), list):
                    events = data["result"]

                elif isinstance(data.get("data"), list):
                    events = data["data"]

            all_events.extend(events)

        except Exception:
            pass

    return channel, all_events


print("Loading channels...")

r = session.get(
    CHANNELS_URL,
    headers=HEADERS,
    timeout=30
)

channels = r.json()["result"]

print(f"Loaded {len(channels)} channels")

programme_count = 0

with gzip.open(
    "epg.xml.gz",
    "wt",
    encoding="utf-8",
    compresslevel=5
) as xml:

    xml.write('<?xml version="1.0" encoding="UTF-8"?>\n')
    xml.write('<tv generator-info-name="JioTV XMLTV Generator">\n')

    print("Writing channels...")

    for ch in channels:

        xml.write(
            f'<channel id="{ch["channel_id"]}">'
        )

        xml.write(
            f'<display-name>{escape(ch["channel_name"])}</display-name>'
        )

        if ch.get("logoUrl"):
            xml.write(
                f'<icon src="{CHANNEL_LOGO_BASE}{ch["logoUrl"]}"/>'
            )

        xml.write('</channel>\n')

    print("Fetching 7-day EPG...")

    with ThreadPoolExecutor(max_workers=200) as executor:

        futures = [
            executor.submit(fetch_epg, ch)
            for ch in channels
        ]

        for future in as_completed(futures):

            result = future.result()

            if not result:
                continue

            channel, events = result

            seen = set()

            for item in events:

                start = xmltv_time(
                    item.get("startEpoch")
                )

                stop = xmltv_time(
                    item.get("endEpoch")
                )

                if not start or not stop:
                    continue

                event_id = (
                    channel["channel_id"],
                    start,
                    stop
                )

                if event_id in seen:
                    continue

                seen.add(event_id)

                xml.write(
                    f'<programme start="{start}" stop="{stop}" channel="{channel["channel_id"]}">'
                )

                title = item.get(
                    "showname",
                    item.get("title", "Unknown")
                )

                xml.write(
                    f'<title lang="en">{escape(title)}</title>'
                )

                if item.get("episodePoster"):
                    xml.write(
                        f'<icon src="{PROGRAM_IMAGE_BASE}{item["episodePoster"]}"/>'
                    )

                desc = (
                    item.get("description")
                    or item.get("synopsis")
                )

                if desc:
                    xml.write(
                        f'<desc lang="en">{escape(desc)}</desc>'
                    )

                category = (
                    item.get("showCategory")
                    or item.get("genre")
                )

                if category:
                    xml.write(
                        f'<category>{escape(category)}</category>'
                    )

                xml.write('</programme>\n')

                programme_count += 1

    xml.write('</tv>\n')

print()
print("Done")
print(f"Channels   : {len(channels)}")
print(f"Programmes : {programme_count}")
print("Output     : epg.xml.gz")