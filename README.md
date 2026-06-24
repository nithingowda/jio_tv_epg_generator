# Indian TV EPG Generator

Generate an XMLTV EPG (Electronic Program Guide) for Indian TV channels and automatically compress it to `epg.xml.gz`.

## Requirements

* Python 3.8+
* Internet connection

Install dependencies:

```bash
pip install -r requirements.txt
```

or

```bash
pip install requests
```

## Files

* `indianepg.py` - Main EPG generator script
* `requirements.txt` - Python dependencies
* `epg.xml.gz` - Generated compressed XMLTV EPG file

## Usage

Run the generator:

```bash
python indianepg.py
```

The script will:

1. Download channel information.
2. Fetch EPG data for all available channels.
3. Generate an XMLTV file.
4. Compress the XMLTV file into `epg.xml.gz`.

## Output

After successful execution, the following file will be created:

```text
epg.xml.gz
```

This file can be used with:

* Jellyfin
* Plex
* Emby
* Kodi
* IPTV Players
* Dispatcharr
* Threadfin
* TVHeadend
* Any XMLTV-compatible application

## Notes

* Generation time depends on the number of channels and API response speed.
* Ensure your internet connection remains active during the process.
* If the script is interrupted, simply run it again.

## Example

```bash
python indianepg.py
```

Expected output:

```text
Loading channels...
Fetching EPG data...
Generating XMLTV...
Compressing epg.xml.gz...
Done!
```

## License

For personal and educational use only.
