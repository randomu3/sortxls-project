import re
import pandas as pd
import phonenumbers
from collections import defaultdict
from validate_email import validate_email
from email_validator import validate_email, EmailNotValidError
import logging
from dictionary import states_regex, common_first_names, common_last_names, common_cities, countries_regex

# Настройка логирования
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Обновление регулярных выражений
possible_columns = {
    'Fullname': re.compile(r'^(?![\s.]+$)[a-zA-Z\s.]{2,50}(?<!\s)$', re.IGNORECASE),
    'First name': re.compile(r'^(?![\s.]+$)[a-zA-Z\s.]{2,30}$', re.IGNORECASE),
    'Last name': re.compile(r'^(?![\s.]+$)[a-zA-Z\s.]{2,30}$', re.IGNORECASE),
    'Zip': re.compile(r'^\d{5}(-\d{4})?$', re.IGNORECASE),
    'City': re.compile(r'^(?![\s.]+$)[a-zA-Z\s.-]+$', re.IGNORECASE),
    'State': re.compile(r'^(?![\s.]+$)[a-zA-Z\s.]{2,50}$', re.IGNORECASE),
    'Address': re.compile(r'^\d+\s+[\w\s.-]+(\s+[\w\s.-]+)*$', re.IGNORECASE),  # Обновлено для учета номеров квартир
    'Phone': re.compile(r'^\d{10,}$'),  # Обновленный шаблон для телефонов
    'Country': re.compile(r'^(?![\s.]+$)[a-zA-Z\s.]{2,50}$', re.IGNORECASE),
    'Email': re.compile(r'^[\w.-]+@[\w.-]+\.\w+$', re.IGNORECASE)  # Обновлено для учета дополнительных символов
}

def sanitize_email(email):
    return email.strip().lower().rstrip('a,.')  # Add any other characters to strip as needed

# Функция для проверки телефонного номера
def is_valid_phone(number, country="US"):
    try:
        phone_number = phonenumbers.parse(number, country)
        return phonenumbers.is_valid_number(phone_number)
    except phonenumbers.NumberParseException as e:
        logging.error(f"Error parsing phone number {number}: {e}")
        return False

def is_valid_email(email):
    try:
        # Validate
        v = validate_email(email)
        # Replace with normalized form
        email = v["email"]
        return True
    except EmailNotValidError as e:
        # Email is not valid, exception message is human-readable
        logging.error(str(e))
        return False

# Implement resolve_ambiguous_columns function
def resolve_ambiguous_columns(candidates, col_data):
    if 'Email' in candidates and 'Phone' in candidates:
        email_count = sum(1 for item in col_data if possible_columns['Email'].match(item))
        phone_count = sum(1 for item in col_data if possible_columns['Phone'].match(item))
        if email_count > phone_count:
            return 'Email'
        else:
            return 'Phone'
    # Additional checks for 'City' vs 'Unknown'
    if 'City' in candidates and 'Unknown' in candidates:
        city_count = sum(1 for item in col_data if item in common_cities)
        if city_count > 0:
            return 'City'
    # Пример использования словарей для разрешения неоднозначности между именем и фамилией
    if 'First name' in candidates and 'Last name' in candidates:
        first_name_count = sum(1 for item in col_data if item in common_first_names)
        last_name_count = sum(1 for item in col_data if item in common_last_names)
        if first_name_count > last_name_count:
            return 'First name'
        else:
            return 'Last name'
    return candidates[0]

# Function to identify if a string is a city name using heuristics
def is_possible_city(item):
    # Check if the item is in the common cities dictionary
    if item in common_cities:
        return True

    # Use regular expressions to check for common city name patterns
    city_pattern = re.compile(r'^(?![\s.]+$)[a-zA-Z\s.-]+$', re.IGNORECASE)
    if city_pattern.match(item):
        # Additional heuristics can be implemented here
        # For example, checking if the item is capitalized (common for city names)
        if item.istitle():
            return True
        # Checking for common city suffixes like "City", "Town", "Village", etc.
        common_city_suffixes = ['city', 'town', 'village', 'borough', 'burgh', 'port', 'haven', 'falls', 'dale', 'field']
        if any(item.lower().endswith(suffix) for suffix in common_city_suffixes):
            return True
    return False

# Функция для определения типа столбца
def identify_column(col_data):
    column_matches = defaultdict(int)

    for item in col_data:
        item = str(item).strip().lower()
        matched = False

        for column_name, pattern in possible_columns.items():
            if pattern.match(item):
                if column_name == 'Phone' and not is_valid_phone(item):
                    continue
                if column_name == 'Email' and not is_valid_email(item):
                    continue

                # Additional check for State column using the states_regex dictionary
                if column_name == 'State' and not any(states_regex[state].match(item) for state in states_regex):
                    continue

                # Additional check for Country column using the countries_regex dictionary
                if column_name == 'Country' and not any(countries_regex[country].match(item) for country in countries_regex):
                    continue

                # Additional logic to differentiate between Fullname, First name, and Last name
                if column_name in ['Fullname', 'First name', 'Last name']:
                    name_parts = item.split()
                    if column_name == 'Fullname' and len(name_parts) < 2:
                        continue
                    if column_name == 'First name' and item not in common_first_names:
                        continue
                    if column_name == 'Last name' and item not in common_last_names:
                        continue

                # Improved check for cities using the is_possible_city function
                if column_name == 'City' and is_possible_city(item):
                    column_matches[column_name] += 1
                    matched = True
                    continue  # Skip other checks for cities

                column_matches[column_name] += 1
                matched = True
                break

        if not matched:
            # Additional logic to handle unknown data
            if item.isdigit():
                column_matches['Numeric'] += 1
            elif any(keyword in item for keyword in ['street', 'ave', 'road']):
                column_matches['Address'] += 1
            else:
                column_matches['Unknown'] += 1

    # Select the most likely column type
    if not column_matches:
        return 'Unknown'

    sorted_matches = sorted(column_matches.items(), key=lambda x: x[1], reverse=True)
    most_likely_column = sorted_matches[0][0]

    # Check for maximum number of matches
    max_matches = max(column_matches.values())
    candidates = [col for col, matches in column_matches.items() if matches == max_matches]

    # Resolve ambiguities
    if len(candidates) > 1:
        return resolve_ambiguous_columns(candidates, col_data)
    
    return most_likely_column

# Function to process a file and identify columns using pandas
def process_file_with_pandas(file_path):
    # Read the file into a pandas DataFrame
    logging.info(f"Processing file: {file_path}")
    try:
        df = pd.read_csv(file_path, delimiter='|', header=None, error_bad_lines=False)
    except Exception as e:
        logging.error(f"Ошибка при чтении файла: {e}")
        return None
    # Transpose the DataFrame to work with columns as rows
    transposed_df = df.T
    # Identify each column
    column_names = [identify_column(col.astype(str)) for col in transposed_df.values]
    return '|'.join(column_names)

# Функция для сравнения результатов с тестовыми файлами и вывода содержимого
def compare_and_print_contents(file_path, test_file_path, identified_columns):
    with open(file_path, 'r') as file:
        original_content = file.read().strip()
    with open(test_file_path, 'r') as test_file:
        test_content = test_file.read().strip()
    
    if test_content == identified_columns:
        logging.info(f"File {file_path} matches the test file {test_file_path}")
    else:
        logging.warning(f"File {file_path} does not match the test file {test_file_path}")

    # Вывод содержимого оригинального и тестового файлов
    print(f"Original File: {file_path}\n{original_content}")
    print(f"Test File: {test_file_path}\n{test_content}")
    
    # Сравнение идентифицированных столбцов с тестовым файлом
    return test_content == identified_columns

# Main function to compare and print file contents
def main():
    # List of file paths to be processed
    file_paths = ['files/5.txt']
    # List of test file paths for comparison
    test_paths = ['5tst.txt']

    # Process each file and compare the results with the test files
    for file_path, test_path in zip(file_paths, test_paths):
        identified_columns = process_file_with_pandas(file_path)
        comparison_result = compare_and_print_contents(file_path, test_path, identified_columns)

        # Print the comparison result
        if comparison_result:
            print(f"Results match with {test_path}")
        else:
            print(f"Results do NOT match with {test_path}")
            print(f"Identified Columns: {identified_columns}\n")

# Call the main function
if __name__ == "__main__":
    main()