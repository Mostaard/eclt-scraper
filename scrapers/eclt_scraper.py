import json
import logging
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import re
import yaml
from bs4 import BeautifulSoup
from scrapers.jsparser import Parser

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# Set variables depending on the environment
MODEL_NAME = 'tutori_eclt_legacy.LegacyExercise'
delimiter = '/'


class JavascriptVariableScraper:
    soup = None
    script = None
    file = None

    def set_file(self, file):
        self.file = file
        try:
            with open(file, encoding='utf8') as fh:
                self.soup = BeautifulSoup(fh.read(), features="html.parser")
                self.set_trimmed_script()
        except UnicodeDecodeError as e:
            logging.error(f'Problem loading {self.file} - {e}')

    def set_trimmed_script(self):
        try:
            if self.soup:
                title = self.soup.find('title')
                if title:
                    self.page_title = title.text or ''
                else:
                    self.page_title = ''

                # self.script = str(self.soup.find_all('script', attrs={'src': False})[0].string).replace('<!--', '').replace(
                #     '-->', '').replace('#', '').replace(r'http://', '').replace(r'https://', '')
                self.script = str(self.soup.find_all('script', attrs={'src': False})[0].string).replace('<!--', '').replace(
                    '-->', '').replace(r'http://', '').replace(r'https://', '')

                # Remove simple comments
                self.script = re.sub(r'//.*\n', '', self.script)

                # Fix AV scripts
                if self.script[-1] == '>':
                    self.script += "');}"

                # Fix Tonos scripts
                self.script = self.script.replace('";\n" </ol>', '</ol>')
                self.script = self.script.replace('";\n\n" </ol>', '</ol>')

                # Fix Uitspraak scripts
                self.script = self.script.replace(
                    '"\n                    "', '')
                
                # Fix 'juistepr1per1' scripts by removing breedteTV and hoogteTV lines from scripts (they are not needed and break the parser)
                self.script = re.sub(r'var breedteTV.*\n', '', self.script)
                self.script = re.sub(r'var hoogteTV.*\n', '', self.script)

        except IndexError:
            logging.error(f'No suitable script found in {self.file}')


class ErrorMargin:
    success_counter = 0
    error_counter = 0
    min_entries = 20
    margin = .05

    def __init__(self, scraper):
        self.scraper = scraper

    def success(self):
        self.success_counter = self.success_counter + 1

    def error(self):
        self.error_counter = self.error_counter + 1
        logging.info(
            f'Error occurred at {self.scraper.exercise}, current error rate is {self.error_rate()}, accepted error margin is {self.error_margin()}')
        self.check()

    def error_rate(self):
        if self.scraper.counter == 0:
            return 1
        return self.error_counter / self.scraper.counter

    def error_margin(self):
        return self.margin

    def check(self):
        if self.scraper.counter > self.min_entries and self.error_rate() > self.margin:
            raise Exception('Margin of error breached')


class ExerciseScraper:
    def __init__(self, exercise: str, exclude, tutori_model):
        self.exercise = exercise
        self.exclude = exclude
        self.folder_scraper = FolderScraper(exercise)
        self.js_scraper = JavascriptVariableScraper()
        self.tutori_model = tutori_model
        self.result = []
        self.error_margin = ErrorMargin(self.folder_scraper)

    def scrape_exercise(self, exercise_path):
        self.js_scraper.set_file(exercise_path)
        exercise = dict()
        exercise['model'] = self.tutori_model
        exercise['pk'] = None
        exercise['fields'] = dict()
        exercise['fields']['ex_type'] = self.exercise.lower()
        exercise['fields']['file_name'] = exercise_path.split(
            delimiter)[-1]
        exercise['fields']['language'] = exercise_path.split(
            delimiter)[-2]
        exercise['fields']['page_title'] = self.js_scraper.page_title
        exercise['fields']['data'] = self.retrieve_vars()

        # Type specific fields
        if self.exercise.lower() == 'avrecorder':
            if self.js_scraper.soup:
                opgave_div = self.js_scraper.soup.find(
                    'div', attrs={'id': 'opgave'})
                opgave = opgave_div.text.replace(
                    '../../../', 'https://e-lan.be/').replace('\t', '') if opgave_div else ''
                exercise['fields']['data']['opgave'] = opgave

        self.result.append(exercise)

    def run(self):
        for exercise in [e for e in self.folder_scraper.exercises if
                         (e.split(delimiter)[-2] not in self.exclude and e.split(delimiter)[-1] not in self.exclude)]:
            self.scrape_exercise(exercise)
            self.folder_scraper.increment_and_log()

    def retrieve_vars(self):
        fields = dict()
        try:
            if not self.js_scraper.script:
                raise Exception('No script found')
            parser = Parser(self.js_scraper.script)
            with open('scrapers/output/parsed_data.json', 'w', encoding='utf-8') as f:
                json.dump(parser.data, f, ensure_ascii=False, indent=4)
            fields = parser.parsed_data
            self.error_margin.success()
        except Exception as e:
            logging.error(e)
            self.error_margin.error()
        return fields

    def add_result(self, language, exercise, key, value):
        if exercise not in self.result[language]:
            self.result[language][exercise] = defaultdict()
        self.result[language][exercise][key] = value


class FolderScraper:
    base_folder = 'scrapers/data/Muis/{}'
    suffixes = [".htm", ".html"]
    exercises = []
    counter = 0
    start = datetime.now()

    def __init__(self, exercise: str):
        self.exercise = exercise
        self.exercise_name = self.exercise.split(delimiter)[-1]
        self.retrieve_exercise_paths()

    def get_folder(self):
        return self.base_folder.format(self.exercise)

    def retrieve_exercise_paths(self):
        path_list = Path(self.get_folder()).glob('**/*')
        for path in path_list:
            if path.suffix in self.suffixes:
                self.exercises.append(str(path))

    def increment_and_log(self):
        self.counter = self.counter + 1
        logging.debug(
            f'Finished exercise {self.counter} of {len(self.exercises)}')
        if self.counter % 100 == 0:
            time_passed = datetime.now() - self.start
            avg_per_exercise = time_passed / self.counter
            time_todo = avg_per_exercise * (len(self.exercises) - self.counter)
            logging.info(
                f'\n{self.exercise_name} will finish processing in {time_todo}\nprocessed {self.counter} exercises')


def run_one():
    """When running one make sure def-config.yml configuration is set to the correct exercise"""
    with open('./dev-config.yml', 'r') as f:
        conf = yaml.safe_load(f)
        for key, value in conf.items():
            scraper = ExerciseScraper(
                key, value['exclude'].split(','), value.get('model'))
            scraper.scrape_exercise(
                '../data/Invul1Per1/En4/GreenSpaces_linkwordsINV1.htm')
            log.info('finished')
            f = open("./scrapers/output/out.json", "w+", encoding="utf-8")
            f.write(json.dumps(scraper.result, ensure_ascii=False))
            f.close()
            log.info(scraper.js_scraper.script)


def run():
    with open('dev-config.yml', 'r') as f:
        conf = yaml.safe_load(f)
        for key, value in conf.items():
            scraper = ExerciseScraper(
                key, value['exclude'].split(','), value.get('model', MODEL_NAME))
            scraper.run()
            # scraper.close()
            f = open(
                f"scrapers/output/{key.lower()}.json", "w+", encoding="utf-8")
            f.write(json.dumps(scraper.result, ensure_ascii=False))
            f.close()


run()
