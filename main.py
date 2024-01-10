# main.py
import pandas as pd
import re
import os

# Определение функций для проверки содержимого столбцов
def is_email(s):
    return bool(re.match(r"[^@]+@[^@]+\.[^@]+", s))

def is_phone(s):
    return bool(re.match(r"(\+\d{1,3})?[\s-]?(\(\d{3}\))?[\s-]?\d{3}[\s-]?\d{2}[\s-]?\d{2}", s))

def is_country(s):
    return s.lower() in ['us', 'usa', 'united states', 'unitedstates']

def is_fullname(s):
    return " " in s  # Простое предположение, что полное имя содержит пробел

def is_name(s):
    # Имя обычно содержит только буквы, может включать апострофы или тире
    return bool(re.match(r"^[a-zA-Zа-яА-ЯёЁ-]+[a-zA-Zа-яА-ЯёЁ' -]*$", s))

def is_address(s):
    # Адрес обычно содержит цифры и слова, может включать названия улиц
    return bool(re.search(r'\d', s)) and bool(re.search(r'\D', s))

def is_zip(s):
    # ZIP код обычно содержит только цифры (простая версия)
    return s.isdigit()

def is_city_or_state(s):
    # Город или штат обычно содержат только буквы, может включать пробелы и специальные символы
    return bool(re.match(r"^[a-zA-Zа-яА-ЯёЁ .-]+$", s))

# Функция определения столбцов
def identify_columns(df):
    column_mapping = {}
    used_titles = set()  # Для отслеживания уже использованных заголовков

    for col in df.columns:
        sample_data = df[col].dropna().astype(str)

        # Проверка каждого условия и обновление соответствующих заголовков
        if 'Email' not in used_titles and sample_data.apply(is_email).any():
            column_mapping[col] = 'Email'
            used_titles.add('Email')
        elif 'Phone' not in used_titles and sample_data.apply(is_phone).any():
            column_mapping[col] = 'Phone'
            used_titles.add('Phone')
        elif 'Country' not in used_titles and sample_data.apply(is_country).any():
            column_mapping[col] = 'Country'
            used_titles.add('Country')
        elif 'Fullname' not in used_titles and sample_data.apply(is_fullname).any():
            column_mapping[col] = 'Fullname'
            used_titles.add('Fullname')
        # Добавьте здесь логику для остальных столбцов, например, для 'First name', 'Last name', 'Address', 'City', 'State', 'Zip'

    return column_mapping

# Функция обработки файла
def process_file(file_path):
    df = pd.read_csv(file_path, delimiter='|')

    # Определение столбцов
    mapping = identify_columns(df)

    # Перестановка столбцов
    ordered_columns = ['Fullname', 'Address', 'City', 'State', 'Zip', 'Country', 'Phone', 'Email']
    df = df.rename(columns=mapping)
    final_columns = [col for col in ordered_columns if col in df.columns]
    df = df[final_columns]

    # Сохранение в новый файл
    file_name, file_extension = os.path.splitext(os.path.basename(file_path))
    new_filename = 'processed_' + file_name + file_extension
    new_file_path = os.path.join(os.path.dirname(file_path), new_filename)

    # В начало файла добавляем строку с названием и форматом старого файла
    with open(new_file_path, 'w') as new_file:
        new_file.write(f'Original File: {file_name}{file_extension}\n')
        df.to_csv(new_file, index=False, header=True)

    return new_file_path

# Пример использования
process_file('files/4.txt')
