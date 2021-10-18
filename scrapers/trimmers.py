import re


def semi_colonize(script: str):
    result = []
    script_list = script.replace('\t', '').split('\n')
    for i, line in enumerate(script_list):
        line = line.strip()
        if len(line) > 2:
            if line[-1] not in [';', '+'] and i + 1 < len(script_list):
                line = line + ';'
            result.append(line)
    return '\n'.join(result)


def general_trimmer(script, reassigned, initializers, variables):
    script = semi_colonize(script)
    var_list = []
    for var in variables:
        result = re.findall(r'var ' + var + r'.*?;\n', script, re.DOTALL)
        if result:
            var_list.append(result[0])
    if reassigned:
        for list_name in reassigned['lists'].split(','):
            var_list = var_list + re.findall(list_name + r'\[.*?;\n', script, re.DOTALL)
    if initializers:
        for key, value in initializers.items():
            var_list.insert(0, 'var {} = {};\n'.format(key, value))

    return ''.join(var_list)


# def general_trimmer(self):
#     try:
#         self.script = str(self.soup.find_all('script', attrs={'src': False})[0].string).replace('<!--', '').replace(
#             '-->', '').replace('#', '').replace(r'http://', '').replace(r'https://', '')
#     except IndexError:
#         logging.error('No suitable script found in {}'.format(self.file))
#     self.script = re.sub(r'/[*][\s\S]{0,2000}[*]/', '', self.script)
#     self.script = re.sub('//.{0,500}\n', '', self.script)
#     self.script = re.sub(';.\n', ';\n', self.script)
#     self.script = re.sub(r'if \( \(AVallowedExtensions.{0,500}\n', '', self.script)
#     self.script = re.sub(r'if \(!LnaarR\).{0,500}\n', '', self.script)
#     self.script = re.sub(r'{document.write\(\'<script type=\"text/javascript".{0,500}\n', '', self.script)
#     self.script = semi_colonize(self.script)
#     var_list = re.findall(r'\n {0,3}var [\s\S]{1,700};\n', self.script) + re.findall(r'help\[.\].{1,500};\n',
#                                                                                      self.script)
#     if self.reassigned:
#         for list_name in self.reassigned['lists'].split(','):
#             var_list = var_list + re.findall(list_name + r'\[.\].{1,600};\n', self.script)
#     if self.initializers:
#         for key, value in self.initializers.items():
#             var_list.insert(0, 'var {} = {};\n'.format(key, value))
#
#     self.script = ''.join(var_list)
trimmer = {
    'Alfabet': general_trimmer
}
