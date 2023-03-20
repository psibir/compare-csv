import argparse
import csv
import os
import Levenshtein
from typing import List
from fuzzywuzzy import fuzz
from deepdiff import DeepDiff


class CsvFile:
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.headers = None
        self.rows = None

    def load(self):
        with open(self.filepath, 'r', newline='') as f:
            reader = csv.reader(f)
            self.headers = next(reader)
            self.rows = [row for row in reader]

    def validate(self, other: 'CsvFile'):
        if self.headers != other.headers:
            raise ValueError('Files have different headers')

    def find_matches(self, other: 'CsvFile', threshold: int, algorithm: str) -> List[List[str]]:
        matches = []
        for row in self.rows:
            for other_row in other.rows:
                if algorithm == 'fuzzywuzzy':
                    similarity = fuzz.ratio(row, other_row)
                elif algorithm == 'levenshtein':
                    similarity = 100 - Levenshtein.distance(row, other_row) / max(len(row), len(other_row)) * 100
                else:
                    raise ValueError('Invalid algorithm')

                if similarity >= threshold:
                    matches.append(row)
                    break
        return matches

    def find_differences(self, other, threshold, algorithm='fuzzywuzzy'):
        differences = []
        other_rows = [row for row in other.rows]
        for i, row1 in enumerate(self.rows):
            found_match = False
            for j, row2 in enumerate(other_rows):
                if algorithm == 'fuzzywuzzy':
                    score = fuzz.token_sort_ratio(row1, row2)
                elif algorithm == 'levenshtein':
                    score = 100 - (Levenshtein.distance(row1, row2) / len(row1) * 100)
                else:
                    raise ValueError('Invalid algorithm')
                if score >= threshold:
                    other_rows.pop(j)
                    found_match = True
                    break
            if not found_match:
                differences.append(row1 + ['csv1'])
        for row2 in other_rows:
            differences.append(row2 + ['csv2'])
        return differences


class CSVComparator:
    def __init__(self, file1: CsvFile, file2: CsvFile):
        self.file1 = file1
        self.file2 = file2

    def compare(self, algorithm: str) -> DeepDiff:
        self.file1.validate(self.file2)
        return DeepDiff(self.file1.rows, self.file2.rows, ignore_order=True, ignore_string_case=True)

    def get_matches(self, threshold: int, algorithm: str) -> List[List[str]]:
        self.file1.validate(self.file2)
        return self.file1.find_matches(self.file2, threshold, algorithm)

    def get_differences(self, threshold: int, algorithm: str) -> List[List[str]]:
        self.file1.validate(self.file2)
        return self.file1.find_differences(self.file2, threshold, algorithm)


def write_csv(filepath: str, headers: List[str], rows: List[List[str]]):
    with open(filepath, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description='Compare two CSV files')
    parser.add_argument('file1', type=str, help='First CSV file')
    parser.add_argument('file2', type=str, help='Second CSV file')
    parser.add_argument('--output_dir', type=str, default='./', help='Output directory (default: current directory)')
    parser.add_argument('--threshold', type=int, default=70, help='Matching threshold (default: 70)')
    parser.add_argument('--algorithm', type=str, default='fuzzywuzzy', choices=['fuzzywuzzy', 'levenshtein'], help='Matching algorithm to use (default: fuzzywuzzy)')
    args = parser.parse_args()

    # Load the CSV files
    file1 = CsvFile(args.file1)
    file2 = CsvFile(args.file2)
    file1.load()
    file2.load()

    # Compare the files
    comparator = CSVComparator(file1, file2)
    if args.algorithm == 'fuzzywuzzy':
        differences = comparator.compare('fuzzywuzzy')
    elif args.algorithm == 'levenshtein':
        differences = comparator.compare('levenshtein')
    else:
        raise ValueError('Invalid algorithm')

    # Write the output files
    os.makedirs(args.output_dir, exist_ok=True)
    matches_file = os.path.join(args.output_dir, 'matches.csv')
    differences_file = os.path.join(args.output_dir, 'differences.csv')
    write_csv(matches_file, file1.headers, comparator.get_matches(args.threshold, args.algorithm))
    write_csv(differences_file, file1.headers, comparator.get_differences(args.threshold, args.algorithm))
    print(f'Matches written to {matches_file}')
    print(f'Differences written to {differences_file}')

if __name__ == '__main__':
    main()
