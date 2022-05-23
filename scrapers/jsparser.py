from logging import log
from pyjsparser import parse
import json


class Parser:
    def __init__(self, data: str):
        self.script = data
        try:
            temp_data = parse(data)
        except Exception as e:
            raise e
        self.data: list = temp_data['body'] if isinstance(
            temp_data, dict) else []
        with open('scrapers/output/parsed_data.json', 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=4)
        self.parsed_data = dict()
        self.parse(self.data)

    def parse_declaration(self, declarations):
        for declaration in declarations:
            name = declaration['id']['name']
            if not declaration.get('init', None):
                return
            if declaration['init']['type'] == 'Literal':
                value = declaration['init']['value']
                self.parsed_data[name] = value
            if declaration['init']['type'] == 'ArrayExpression':
                value = declaration['init']['elements']
                self.parsed_data[name] = value
            if declaration['init']['type'] == 'BinaryExpression':
                value = ""
                value += self.resolve_addition(
                    declaration['init'], value)
                self.parsed_data[name] = value
            elif declaration['init']['type'] == 'NewExpression':
                self.parsed_data[name] = []

    def resolve_addition(self, obj, value):
        if obj['type'] == 'BinaryExpression':
            if obj['operator'] == '+':
                value += self.resolve_addition(obj['left'], value)
        else:
            value += obj['value']
            return value

        try:
            value += obj['right']['value']
        except Exception as e:
            print(e)
        return value

    def parse_expression(self, expression):
        if expression['operator'] == '=':
            if expression['left']['type'] == 'Identifier':
                name = expression['left']['name']
                return
            if expression['left']['type'] == 'MemberExpression':
                name = expression['left']['object']['name']
                if name not in self.parsed_data.keys():
                    self.parsed_data[name] = []
            if expression['right']['type'] == 'BinaryExpression' and expression['right']['operator'] == '+':
                value = ""
                value += self.resolve_addition(expression['right'], value)
            else:
                value = expression['right']['value']
            self.parsed_data[name].append(value)

    def parse(self, data):
        try:
            for command in data:
                if command['type'] == 'VariableDeclaration':
                    self.parse_declaration(command['declarations'])
                elif command['type'] == 'ExpressionStatement':
                    self.parse_expression(command['expression'])
        except Exception as e:
            raise e
