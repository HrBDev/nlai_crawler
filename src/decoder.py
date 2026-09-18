"""Decode the UTF-8 bibliographic layouts observed in the NLAI catalog."""

from dataclasses import dataclass

from bs4 import BeautifulSoup


@dataclass
class FetchResult:
    status: str
    data: dict[str, str] | None = None
    http_status: int | None = None
    error: str | None = None


class DecodeError(ValueError):
    pass


# Direction controls are presentation, but ZWNJ/ZWJ are part of Persian text.
_DIRECTION_CONTROLS = str.maketrans('', '', '\u061c\u200e\u200f\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069')


def _text(element):
    text = element.get_text()
    if '\ufffd' in text:
        raise DecodeError('Decoded text contains Unicode replacement characters')
    return ' '.join(text.translate(_DIRECTION_CONTROLS).split())


def decode_record(content: bytes) -> dict[str, str]:
    try:
        html = content.decode('utf-8-sig')
    except UnicodeDecodeError as exc:
        raise DecodeError(f'Invalid UTF-8: {exc}') from exc
    if '\ufffd' in html:
        raise DecodeError('Page contains Unicode replacement characters')
    if '</form>' not in html.lower():
        raise DecodeError('Missing closing form (possibly truncated response)')
    soup = BeautifulSoup(html, 'lxml')
    form = soup.find('form', attrs={'name': 'search_BrowseSearchHitsForm'})
    if form is None:
        raise DecodeError('Bibliographic form is missing')
    content_cell = form.find('td', class_='formcontent')
    if content_cell is None:
        raise DecodeError('Bibliographic content is missing')
    # This slot occurs in both populated and empty captured pages. Width is
    # intentionally ignored; it is a layout attribute, not a field identifier.
    slot = content_cell.find('td', attrs={'height': '30'})
    if slot is None:
        raise DecodeError('Unrecognized bibliographic metadata slot')
    for br in slot.find_all('br'):
        br.replace_with('\n')
    tables = slot.find_all('table')
    if not tables:
        if slot.find() is not None or _text(slot):
            raise DecodeError('Unexpected content in empty metadata slot')
        return {}
    fields = {}
    for row in slot.find_all('tr'):
        cells = row.find_all(['td', 'th'], recursive=False)
        if len(cells) == 1 and cells[0].find('table'):
            continue
        if any(cell.find('table') for cell in cells):
            raise DecodeError('Unexpected nested table inside a bibliographic field')
        if not _text(row):
            continue
        if len(cells) != 3 or _text(cells[1]) != ':':
            raise DecodeError('Malformed bibliographic row: expected label, colon, value')
        key, value = _text(cells[0]), _text(cells[2])
        if not key:
            raise DecodeError('Bibliographic row has an empty label')
        fields[key] = f'{fields[key]} {value}'.strip() if key in fields else value
    if not fields:
        raise DecodeError('Metadata table contains no recognizable fields')
    return fields
