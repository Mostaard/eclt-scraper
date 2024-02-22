import csv
import csv
import logging
from pathlib import Path
from typing import TextIO

from bs4 import BeautifulSoup

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)

header = ['course', 'section', 'section_title', 'ex_type', 'module', 'filename',
          'ex_name', 'test_type']

data = []
modules = []


def scrape_ovp(file: TextIO, group, section):
    soup = BeautifulSoup(file.read(), features="html.parser")
    title = soup.find('title')
    section_title = title.contents[0] if title and title.contents else ''
    for a in soup.find_all('a'):
        row = [group, section, section_title]
        try:
            if a.attrs['href'].startswith("../..") and not a.attrs['href'].endswith(
                    'jpg'):
                link = a.attrs['href'].replace("\\", '/').split("/")
                module = link[4]
                if [module] not in modules:
                    modules.append([module])
                # ex_type
                row.append(link[3])
                row.append(module)
                # filename
                row.append(link[5].split('?')[0])
                # ex_name
                row.append(
                    a.contents[0].replace('\t', '').replace('\n', '').replace(',', ''))
                row.append(link[5].split('?')[1] if len(link[5].split('?')) > 1 else '')
                data.append(row)
        except (KeyError, IndexError, TypeError):
            log.error('something missing')


path_list = Path('data/ovp/CVO-CLT').glob('**/*')
decoding_error = 0
for path in path_list:
    group_info = path.name.split('_')
    if path.suffix == '.htm' and group_info[0] == 'CLT' and len(group_info) >= 4:
        # course
        group = group_info[1]
        # section
        section = group_info[3].replace('.htm', '')
        try:
            with open(path, encoding='utf8') as fh:
                scrape_ovp(fh, group, section)
        except UnicodeDecodeError:
            with open(path, encoding='cp1252') as fh:
                scrape_ovp(fh, group, section)

with open('output/ovp.csv', 'w', encoding='UTF8', newline='') as out:
    writer = csv.writer(out)
    writer.writerow(header)
    for r in data:
        writer.writerow(r)

with open('output/modules.csv', 'w', encoding='UTF8', newline='') as out:
    writer = csv.writer(out)
    writer.writerow(['module', 'language'])
    for r in modules:
        writer.writerow(r)
