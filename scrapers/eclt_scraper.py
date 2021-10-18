import json
import logging
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import yaml
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import JavascriptException

from trimmers import trimmer

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


class JavascriptVariableScraper:
    soup = None
    script = None
    file = None
    reassigned = None
    initializers = None

    def __init__(self, reassigned, initializers, trimmer_function, var_names):
        self.reassigned = reassigned
        self.initializers = initializers
        self.trimmer_function = trimmer_function
        self.var_names = var_names
        self.driver = webdriver.Firefox(executable_path=r'geckodriver.exe')

    def set_file(self, file):
        self.file = file
        try:
            with open(file, encoding='utf8') as fh:
                self.soup = BeautifulSoup(fh.read(), features="html.parser")
                self.set_trimmed_script()
        except UnicodeDecodeError as e:
            logging.error(f'Problem loading {self.file} - {e}')

    def close(self):
        self.driver.close()

    def get_var_value(self, var_name):
        self.set_driver_content(var_name)
        try:
            return self.driver.execute_script('return getValue();')
        except JavascriptException as e:
            if 'getValue' in e.msg:
                raise Exception(f'\n{e}Error in {self.file} - {e}{self.script}\n')
            elif 'is not defined' in e.msg:
                return ''
            else:
                raise Exception(f'\n{e}Error in {self.file} - {e}{self.script}\n')

    def set_driver_content(self, var_name):
        """set the page in the webdriver so that we can run js on it"""
        self.driver.get(f"data:text/html;charset=utf-8,{self.get_proxy_html_page(var_name)}")

    def get_proxy_html_page(self, var_name):
        """returns a html page containing only the javascript code scraped from the file"""
        return f"""
        <html>
             <head>
                <script>
                {self.script}
                function getValue() {{
                     return {var_name};
                    }}
                </script>
             </head>
             <body>
             </body>
        </html>
        """

    def set_trimmed_script(self):
        try:
            self.script = str(self.soup.find_all('script', attrs={'src': False})[0].string).replace('<!--', '').replace(
                '-->', '').replace('#', '').replace(r'http://', '').replace(r'https://', '')
        except IndexError:
            logging.error(f'No suitable script found in {self.file}')
        self.script = self.trimmer_function(self.script, self.reassigned, self.initializers, self.var_names)


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
    def __init__(self, exercise: str, variable_map, exclude, reassigned, initializers, tutori_model):
        self.exercise = exercise
        self.exclude = exclude
        self.folder_scraper = FolderScraper(exercise)
        self.js_scraper = JavascriptVariableScraper(reassigned, initializers, trimmer[exercise], variable_map.keys())
        self.tutori_model = tutori_model
        self.result = []
        self.variable_map = variable_map
        self.error_margin = ErrorMargin(self.folder_scraper)

    def scrape_exercise(self, exercise_path):
        self.js_scraper.set_file(exercise_path)
        exercise = defaultdict()
        exercise['model'] = self.tutori_model
        exercise['language_name'] = exercise_path.split('\\')[-2]
        exercise['exercise_name'] = exercise_path.split('\\')[-1]
        exercise['fields'] = self.retrieve_vars()
        exercise['fields']['exercise_path'] = exercise_path
        self.result.append(exercise)

    def run(self):
        for exercise in [e for e in self.folder_scraper.exercises if
                         (e.split('\\')[-2] not in self.exclude and e.split('\\')[-1] not in self.exclude)]:
            self.scrape_exercise(exercise)
            self.folder_scraper.increment_and_log()

    def retrieve_vars(self):
        fields = defaultdict()
        try:
            for js_key, new_key in self.variable_map.items():
                fields[new_key] = self.js_scraper.get_var_value(js_key)
            self.error_margin.success()
            return fields
        except Exception as e:
            logging.error(e)
            self.error_margin.error()

    def add_result(self, language, exercise, key, value):
        if exercise not in self.result[language]:
            self.result[language][exercise] = defaultdict()
        self.result[language][exercise][key] = value

    def close(self):
        self.js_scraper.close()


class FolderScraper:
    base_folder = 'C:/users/vande/eclt/{}'
    suffixes = [".htm", ".html"]
    exercises = []
    counter = 0
    start = datetime.now()

    def __init__(self, exercise: str):
        self.exercise = exercise
        self.exercise_name = self.exercise.split('\\')[-1]
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
        logging.debug(f'Finished exercise {self.counter} of {len(self.exercises)}')
        if self.counter % 100 == 0:
            time_passed = datetime.now() - self.start
            avg_per_exercise = time_passed / self.counter
            time_todo = avg_per_exercise * (len(self.exercises) - self.counter)
            logging.info(
                f'\n{self.exercise_name} will finnish processing in {time_todo}\nprocessed {self.counter} excersies')


def run_one():
    """When running one make sure def-config.yml configuration is set to the correct exercise"""
    with open('../dev-config.yml', 'r') as f:
        conf = yaml.safe_load(f)
        for key, value in conf.items():
            scraper = ExerciseScraper(key, value['fields'], value['exclude'].split(','),
                                      value.get('reassigned', None), value.get('initializers', None),
                                      value.get('model'))
            scraper.scrape_exercise(
                r'C:\xampp\htdocs\html\Muis\Invul1Per1\En4\GreenSpaces_linkwordsINV1.htm')
            log.info('finished')
            f = open("out.json", "w+")
            f.write(json.dumps(scraper.result))
            f.close()
            log.info(scraper.js_scraper.script)

            scraper.close()


def run():
    with open('../dev-config.yml', 'r') as f:
        conf = yaml.safe_load(f)
        for key, value in conf.items():
            scraper = ExerciseScraper(key, value['fields'], value['exclude'].split(','),
                                      value.get('reassigned', None), value.get('initializers', None),
                                      value.get('model'))
            scraper.run()
            scraper.close()
            f = open("out.json", "w+")
            f.write(json.dumps(scraper.result))
            f.close()


run()
# run_one()
