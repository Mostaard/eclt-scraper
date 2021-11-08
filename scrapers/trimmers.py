import re
from pyjsparser import parse
import json

# NO LONGER IN USE, KEPT FOR POSTERITY AND REFERENCE


def apply_common_fixes(script: str) -> str:
    # Common fixes
    script = script.replace('katrien;d', 'katrien.d')
    return script


def semi_colonize(script: str):
    result = []
    script_list = script.replace('\t', '').replace('&nbsp;', '').split('\n')
    for i, line in enumerate(script_list):
        line = line.strip()
        if len(line) > 2:
            if line[-1] not in [';', '+'] and i + 1 < len(script_list):
                line = line + ';'
            result.append(line)
    return ''.join(result)


def general_trimmer(script, reassigned, initializers):
    script = apply_common_fixes(script)
    script = semi_colonize(script)
    var_list = []
    var_search = re.findall(r'var.*?;', script, re.DOTALL)
    if var_search:
        var_list += var_search
    array_search = re.findall(r'\w*\[\d*\].*?;', script, re.DOTALL)
    if array_search:
        var_list += array_search
    if initializers:
        for key, value in initializers.items():
            var_list.insert(0, 'var {} = {};\n'.format(key, value))

    return ''.join(var_list)
