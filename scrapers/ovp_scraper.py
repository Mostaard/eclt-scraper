import logging
from pathlib import Path
from typing import TextIO

from bs4 import BeautifulSoup

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)


def scrape_ovp(file: TextIO):
    soup = BeautifulSoup(file.read(), features="html.parser")
    for a in soup.find_all('a'):
        try:
            log.info(f"{a.attrs['href']} {a.contents[0]}")
        except (KeyError, IndexError):
            log.error('something missing')


path_list = Path('data/ovp/CVO-CLT').glob('**/*')
decoding_error = 0
for path in path_list:
    group_info = path.name.split('_')
    if path.suffix == '.htm' and group_info[0] == 'CLT' and len(group_info) >= 4:
        log.debug(group_info[1])
        log.debug(group_info[3].replace('.htm', ''))
        try:
            with open(path, encoding='utf8') as fh:
                scrape_ovp(fh)
        except UnicodeDecodeError:
            with open(path, encoding='cp1252') as fh:
                scrape_ovp(fh)
