import os
import configparser

from utils.folder_file_manager import make_directory_if_not_exists

CUR_DIR = os.path.dirname(os.path.abspath(__file__))

INPUT_DIR = make_directory_if_not_exists(os.path.join(CUR_DIR, 'input'))
OUTPUT_DIR = make_directory_if_not_exists(os.path.join(CUR_DIR, 'output'))
PDF_IMAGES_DIR = make_directory_if_not_exists(os.path.join(CUR_DIR, 'pdf_images'))
SAMPLE_DIR = os.path.join(CUR_DIR, 'utils', 'sample')
SAMPLE_PDF = os.path.join(SAMPLE_DIR, 'sample.pdf')
AWS_PDF_STORAGE_BUCKET = 'occupant-pdf'
AWS_RESULT_OBJECT = "inbox/ODPS"
CONFIG_FILE = os.path.join(CUR_DIR, 'config.cfg')

params = configparser.ConfigParser()
params.read(CONFIG_FILE)
json_file = params.get("DEFAULT", "json_name")

VISION_CREDENTIAL_PATH = os.path.join(CUR_DIR, 'utils', 'credential', f'{json_file}')
PROCESSED_FILE = os.path.join(CUR_DIR, 'utils', 'processed_files.txt')

FONT_SIZE = 0.6
FONT_WIDTH = 2
OCCUPANT_SPACING = 83
MOTORIST_SPACING = 145
REPORT_TEXT_POSITION = {"report_number": [470, 35], "crash_date_time": [420, 88], "county": [30, 88],
                        "agency_ncic": [350, 60], "agency": [170, 60], "number_of_unit": [480, 60],
                        "unit_in_error": [525, 60], "crash_severity": [505, 88]}
UINT_TEXT_POSITION = {"unit_number": [30, 63], "owner_name": [50, 63], "owner_address": [23, 83],
                      "owner_phone": [265, 63], "number_of_occupants": [145, 195], "damage_scale": [415, 80],
                      "insurance_company": [65, 147], "policy_number": [185, 147], "year": [300, 127],
                      "make": [350, 127], "model": [350, 147], "unit_type": [35, 220], "report_number": [470, 40]}
MOTORIST_TEXT_POSITION = {"unit_number": [35, 60], "name": [60, 60], "birth_date": [450, 60], "age": [540, 60],
                          "gender": [575, 60], "address": [30, 85], "phone": [405, 85], "injuries": [35, 115],
                          "seating_position": [470, 115], "report_number": [470, 32]}

LOCAL = True
