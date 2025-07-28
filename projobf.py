#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import ast
import marshal
import zlib
import sys
import os
import re
import random
import string
from collections import defaultdict

class CrossModuleObfuscator:
    def __init__(self):
        self.name_map = defaultdict(dict)  # {module: {old_name: new_name}}
        self.used_names = set()
        self.module_imports = defaultdict(set)  # {module: set(imported_names)}
        
    def random_identifier(self, length=12):
        """Генератор уникальных имён"""
        while True:
            name = ''.join(random.choice(string.ascii_letters) for _ in range(length))
            if name not in self.used_names:
                self.used_names.add(name)
                return name
    
    def analyze_project(self, project_dir):
        """Анализ всей структуры проекта"""
        py_files = [f for f in os.listdir(project_dir) if f.endswith('.py')]
        
        # Первый проход: сбор информации об импортах
        for file in py_files:
            with open(os.path.join(project_dir, file), 'r', encoding='utf-8') as f:
                tree = ast.parse(f.read())
                
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        self.module_imports[file].add(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    self.module_imports[file].add(node.module)
    
    def obfuscate_file(self, file_path):
        """Обфускация одного файла с учётом межмодульных зависимостей"""
        with open(file_path, 'r', encoding='utf-8') as f:
            source = f.read()
        
        module_name = os.path.basename(file_path)
        tree = ast.parse(source)
        
        # Собираем все идентификаторы для замены
        identifiers = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
                identifiers.add(node.id)
            elif isinstance(node, ast.FunctionDef):
                identifiers.add(node.name)
            elif isinstance(node, ast.ClassDef):
                identifiers.add(node.name)
            elif isinstance(node, ast.AsyncFunctionDef):
                identifiers.add(node.name)
            elif isinstance(node, ast.arg):
                identifiers.add(node.arg)
        
        # Фильтруем системные и импортированные имена
        identifiers = {
            name for name in identifiers
            if not (name.startswith('__') and name.endswith('__'))
            and name not in dir(__builtins__)
            and name not in self.module_imports[module_name]
        }
        
        # Создаем маппинг имен для этого модуля
        for name in identifiers:
            self.name_map[module_name][name] = self.random_identifier()
        
        # Заменяем имена в коде
        for old_name, new_name in self.name_map[module_name].items():
            source = re.sub(r'\b' + re.escape(old_name) + r'\b', new_name, source)
        
        # Обновляем вызовы между модулями
        for other_module, names in self.name_map.items():
            if other_module != module_name:
                for old_name, new_name in names.items():
                    if old_name in source:
                        source = source.replace(old_name, new_name)
        
        return source
    
    def obfuscate_project(self, project_dir, output_dir):
        """Обфускация всего проекта"""
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        self.analyze_project(project_dir)
        
        for file in os.listdir(project_dir):
            if file.endswith('.py'):
                obfuscated = self.obfuscate_file(os.path.join(project_dir, file))
                with open(os.path.join(output_dir, file), 'w', encoding='utf-8') as f:
                    f.write(obfuscated)
        
        print(f"Проект успешно обфусцирован в {output_dir}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Использование: python obfuscator.py <исходная_папка> <выходная_папка>")
        sys.exit(1)
    
    obfuscator = CrossModuleObfuscator()
    obfuscator.obfuscate_project(sys.argv[1], sys.argv[2])
