import ntpath
import os
import json
import numpy as np
import cv2

from pdf2image import convert_from_path
from src.frame.box_detector import extract_box_lines
from src.frame.tesseract_ocr import extract_digit_roi
from utils.ocr_tool import OCRAPI
from utils.folder_file_manager import save_file, log_print
from settings import LOCAL, CUR_DIR, PDF_IMAGES_DIR


class PDFExtractor:
    def __init__(self):
        self.ocr_tool = OCRAPI()
        self.pdf_info = None
        self.box_row_lines = None
        self.box_col_lines = None
        self.report_page_ret = False

    @staticmethod
    def get_json_boundary(f_json, s_json):

        init_left = f_json["boundingPoly"]["vertices"][0]["x"]
        init_right = s_json["boundingPoly"]["vertices"][1]["x"]
        init_bottom = s_json["boundingPoly"]["vertices"][2]["y"]
        init_height = max((f_json["boundingPoly"]["vertices"][3]["y"] - f_json["boundingPoly"]["vertices"][0]["y"]),
                          (s_json["boundingPoly"]["vertices"][3]["y"] - s_json["boundingPoly"]["vertices"][0]["y"]))

        return init_left, init_right, init_bottom, init_height

    def get_json_candidates(self, json_info, f_json, s_json, diff_left_width=0, diff_right_width=0,
                            diff_bottom_height=0):
        init_left, init_right, init_bottom, init_height = self.get_json_boundary(f_json=f_json, s_json=s_json)
        left, right, top, bottom = self.get_box_boundary(init_left=init_left, init_right=init_right,
                                                         init_bottom=init_bottom, init_height=init_height)
        if diff_left_width != 0:
            left = max(init_left - diff_left_width, left)
        if right == 0:
            right = init_right + diff_right_width
        else:
            if diff_right_width != 0:
                right = min(init_right + diff_right_width, right)
        if diff_bottom_height != 0:
            bottom = min(init_bottom + diff_bottom_height, bottom)
        candidates = []
        for _json in json_info:
            _json_x = _json["boundingPoly"]["vertices"][0]["x"] + \
                      0.4 * (_json["boundingPoly"]["vertices"][1]["x"] - _json["boundingPoly"]["vertices"][0]["x"])
            _json_y = 0.5 * (_json["boundingPoly"]["vertices"][0]["y"] + _json["boundingPoly"]["vertices"][3]["y"])
            if left <= _json_x <= right and top <= _json_y <= bottom:
                candidates.append(_json)

        return candidates, left, right, top, bottom

    def get_box_boundary(self, init_left, init_right, init_bottom, init_height):

        left_line = 0
        right_line = 0
        top_line = init_bottom
        bottom_line = 0

        left_line_gap = None
        right_line_gap = None
        bottom_line_gap = None

        for col_line in self.box_col_lines:
            if init_bottom <= col_line[0] <= init_bottom + init_height * 1.5 or \
                    init_bottom <= col_line[1] <= init_bottom + init_height * 1.5 or \
                    col_line[0] <= init_bottom <= col_line[1] or \
                    col_line[0] <= init_bottom + init_height * 1.5 <= col_line[1]:
                if col_line[2] < init_left:
                    if left_line_gap is None:
                        left_line_gap = abs(col_line[2] - init_left)
                        left_line = col_line[2]
                    else:
                        if left_line_gap > abs(col_line[2] - init_left):
                            left_line_gap = abs(col_line[2] - init_left)
                            left_line = col_line[2]
                elif col_line[2] > init_right:
                    if right_line_gap is None:
                        right_line_gap = abs(col_line[2] - init_right)
                        right_line = col_line[2]
                    else:
                        if right_line_gap > abs(col_line[2] - init_right):
                            right_line_gap = abs(col_line[2] - init_right)
                            right_line = col_line[2]

        for row_line in self.box_row_lines:
            if row_line[0] <= init_left <= row_line[1] or row_line[0] <= init_right <= row_line[1]:
                if row_line[2] > init_bottom:
                    if bottom_line_gap is None:
                        bottom_line_gap = abs(row_line[2] - init_bottom)
                        bottom_line = row_line[2]
                    else:
                        if bottom_line_gap > abs(row_line[2] - init_bottom):
                            bottom_line_gap = abs(row_line[2] - init_bottom)
                            bottom_line = row_line[2]

        return left_line, right_line, top_line, bottom_line

    def perform_ocr_roi_frame(self, f_json, s_json, frame, diff_width, diff_bottom=0):
        init_left, init_right, init_bottom, init_height = self.get_json_boundary(f_json=f_json, s_json=s_json)
        left, right, top, bottom = self.get_box_boundary(init_left=init_left, init_right=init_right,
                                                         init_bottom=init_bottom, init_height=init_height)
        left = max(init_left - diff_width, left)
        right = min(init_right + diff_width, right)
        if diff_bottom != 0:
            bottom = min(init_bottom + diff_bottom, bottom)
        roi_frame = frame[init_bottom - init_height:bottom, left + 3:right - 3]
        # cv2.imshow("roi frame", roi_frame)
        # cv2.waitKey()

        frame_path = os.path.join(CUR_DIR, 'roi_temp.jpg')
        cv2.imwrite(frame_path, roi_frame)
        roi_ocr_result = self.ocr_tool.detect_text(img_path=frame_path)
        candidate = roi_ocr_result["textAnnotations"][1:]
        os.remove(frame_path)

        return candidate

    def extract_report_page(self, json_info, frame_path):

        report_number = ""
        agency = ""
        ncic = ""
        units = ""
        unit_error = ""
        county = ""
        crash_date_time = ""
        # crash_date = ""
        # crash_time = ""
        crash_severity = ""
        ret_county = False

        frame = cv2.imread(frame_path)
        frame_height, frame_width = frame.shape[:2]

        for i, _json in enumerate(json_info):
            if _json["description"].lower() == "local" and json_info[i + 1]["description"].lower() == "report" and \
                    json_info[i + 2]["description"].lower() == "number":
                diff_width = json_info[i + 2]["boundingPoly"]["vertices"][1]["x"] - \
                             _json["boundingPoly"]["vertices"][0]["x"]
                report_candidates, _, _, _, _ = self.get_json_candidates(json_info=json_info, f_json=_json,
                                                                         s_json=json_info[i + 2],
                                                                         diff_left_width=diff_width,
                                                                         diff_right_width=diff_width)
                for candi in report_candidates:
                    if candi["boundingPoly"]["vertices"][3]["y"] - candi["boundingPoly"]["vertices"][0]["y"] > 16:
                        report_number += candi["description"]

            elif _json["description"].lower() == "reporting" and json_info[i + 1]["description"].lower() == "agency":
                json_width = int(0.64 * frame_width) - json_info[i + 1]["boundingPoly"]["vertices"][1]["x"] - 5
                agency_ncic_candidates, _, _, _, _ = self.get_json_candidates(json_info=json_info, f_json=_json,
                                                                              s_json=json_info[i + 1],
                                                                              diff_left_width=10,
                                                                              diff_right_width=json_width)
                for candi in agency_ncic_candidates:
                    candi_des = candi["description"].replace(",", "").replace(".", "")
                    if not candi_des.isdigit():
                        agency += candi_des + " "
                    else:
                        ncic += candi_des

            elif _json["description"].lower() == "number" and json_info[i + 2]["description"].lower() == "units":
                units_candidates, left, right, top, bottom = self.get_json_candidates(json_info=json_info, f_json=_json,
                                                                                      s_json=json_info[i + 2],
                                                                                      diff_left_width=10,
                                                                                      diff_right_width=10)
                for candi in units_candidates:
                    if candi["boundingPoly"]["vertices"][3]["y"] - candi["boundingPoly"]["vertices"][0]["y"] > 16:
                        units += candi["description"] + " "
                if units == "":
                    roi_frame = frame[top:bottom, left:right]
                    units = extract_digit_roi(roi_frame=roi_frame)

            elif _json["description"].lower() == "unit" and json_info[i + 2]["description"].lower() == "error":
                diff_width = json_info[i + 1]["boundingPoly"]["vertices"][1]["x"] - \
                             _json["boundingPoly"]["vertices"][0]["x"]
                unit_error_candidates, left, right, top, bottom = self.get_json_candidates(json_info=json_info,
                                                                                           f_json=_json,
                                                                                           s_json=json_info[i + 2],
                                                                                           diff_left_width=diff_width,
                                                                                           diff_right_width=diff_width)
                json_height = abs(_json["boundingPoly"]["vertices"][0]["y"] -
                                  _json["boundingPoly"]["vertices"][3]["y"])
                for candi in unit_error_candidates:
                    candi_height = abs(candi["boundingPoly"]["vertices"][0]["y"] -
                                       candi["boundingPoly"]["vertices"][3]["y"])
                    if candi_height > json_height + 2 and \
                            candi["description"].lower() not in ["98", "99", "animal", "unknown", "-"]:
                        unit_error += candi["description"]

                if unit_error == "":
                    unit_error = extract_digit_roi(roi_frame=frame[top:bottom, left:right], base_height=json_height)
                unit_error = unit_error.replace("99", "").replace("98", "")

            elif _json["description"].lower() == "county" and not ret_county:
                county_candidates, left, right, top, bottom = self.get_json_candidates(json_info=json_info,
                                                                                       f_json=_json,
                                                                                       s_json=_json,
                                                                                       diff_left_width=10,
                                                                                       diff_right_width=15)
                for candi in county_candidates:
                    county += candi["description"]
                ret_county = True
                if county == "":
                    county = extract_digit_roi(roi_frame=frame[top:bottom, left:right])

            elif _json["description"].lower() == "crash" and json_info[i + 3]["description"].lower() == "time":
                diff_width = _json["boundingPoly"]["vertices"][1]["x"] - _json["boundingPoly"]["vertices"][0]["x"]
                crash_date_time_candidates, _, _, _, _ = self.get_json_candidates(json_info=json_info, f_json=_json,
                                                                                  s_json=json_info[i + 3],
                                                                                  diff_left_width=diff_width,
                                                                                  diff_right_width=diff_width)
                crash_date_time = ""
                for candi in crash_date_time_candidates:
                    crash_date_time += candi["description"] + "  "
                crash_date_time = crash_date_time.replace("/", "  ")
                # crash_date = crash_date_time.split(" ")[0]
                # crash_time = crash_date_time.split(" ")[1]

            elif _json["description"].lower() == "crash" and json_info[i + 1]["description"].lower() == "severity":
                diff_width = _json["boundingPoly"]["vertices"][1]["x"] - _json["boundingPoly"]["vertices"][0]["x"]
                crash_severity_candidates, left, right, top, bottom = \
                    self.get_json_candidates(json_info=json_info, f_json=_json, s_json=json_info[i + 1],
                                             diff_left_width=diff_width)
                json_height = abs(_json["boundingPoly"]["vertices"][0]["y"] -
                                  _json["boundingPoly"]["vertices"][3]["y"])
                for candi in crash_severity_candidates:
                    candi_height = abs(candi["boundingPoly"]["vertices"][0]["y"] -
                                       candi["boundingPoly"]["vertices"][3]["y"])
                    if candi["boundingPoly"]["vertices"][0]["x"] < _json["boundingPoly"]["vertices"][0]["x"] and \
                            candi_height > json_height + 2:
                        crash_severity += candi["description"]
                    if len(crash_severity) != 1:
                        if crash_severity == "11":
                            crash_severity = "1"
                        else:
                            crash_severity = crash_severity.replace("1", "")
                if crash_severity == "":
                    crash_severity = extract_digit_roi(roi_frame=frame[top:bottom, left:right], base_height=json_height,
                                                       base_line_x=_json["boundingPoly"]["vertices"][0]["x"])

        return report_number, crash_date_time, crash_severity, county, ncic, agency, units, unit_error

    def extract_unit_page(self, json_info, frame_path):

        unit_number = ""
        owner_name = ""
        owner_address = ""
        owner_phone = ""
        occupants = ""
        damage_scale = ""
        insurance_company = ""
        policy_number = ""
        vehicle_year = ""
        vehicle_make = ""
        vehicle_model = ""
        unit_type = ""

        frame = cv2.imread(frame_path)
        frame_height, frame_width = frame.shape[:2]

        for i, _json in enumerate(json_info):
            if _json["description"].lower() == "unit" and json_info[i + 1]["description"].lower() == "#":
                unit_number_candidates, left, right, top, bottom = self.get_json_candidates(json_info=json_info,
                                                                                            f_json=_json,
                                                                                            s_json=json_info[i + 1],
                                                                                            diff_bottom_height=40,
                                                                                            diff_right_width=15)
                for candi in unit_number_candidates:
                    unit_number += candi["description"]
                if unit_number == "":
                    unit_number = extract_digit_roi(roi_frame=frame[top:bottom, left:right])

            elif _json["description"].lower() == "owner" and json_info[i + 1]["description"].lower() == "name":
                owner_name_candidates, _, _, _, _ = self.get_json_candidates(json_info=json_info, f_json=_json,
                                                                             s_json=json_info[i + 1],
                                                                             diff_bottom_height=40, diff_left_width=10)
                sorted_owner_name_candidates = sorted(owner_name_candidates,
                                                      key=lambda k: k["boundingPoly"]["vertices"][0]["x"])
                for candi in sorted_owner_name_candidates:
                    owner_name += candi["description"] + " "

            elif _json["description"].lower() == "owner" and json_info[i + 1]["description"].lower() == "address":
                json_width = int(0.64 * frame_width) - json_info[i + 1]["boundingPoly"]["vertices"][1]["x"] - 5
                owner_address_candidates, _, _, _, _ = self.get_json_candidates(json_info=json_info, f_json=_json,
                                                                                s_json=json_info[i + 1],
                                                                                diff_bottom_height=40,
                                                                                diff_right_width=json_width)
                for candi in owner_address_candidates:
                    owner_address += candi["description"] + " "

            elif _json["description"].lower() == "owner" and json_info[i + 1]["description"].lower() == "phone":
                json_width = int(0.64 * frame_width) - json_info[i + 1]["boundingPoly"]["vertices"][1]["x"] - 5
                owner_phone_candidates, _, _, _, _ = self.get_json_candidates(json_info=json_info, f_json=_json,
                                                                              s_json=json_info[i + 2],
                                                                              diff_right_width=json_width)
                sorted_owner_phone_candidates = sorted(owner_phone_candidates,
                                                       key=lambda k: k["boundingPoly"]["vertices"][0]["x"])

                for candi in sorted_owner_phone_candidates:
                    if 0.5 * (candi["boundingPoly"]["vertices"][0]["x"] + candi["boundingPoly"]["vertices"][1]["x"]) > \
                            _json["boundingPoly"]["vertices"][0]["x"] and \
                            candi["boundingPoly"]["vertices"][3]["y"] - candi["boundingPoly"]["vertices"][0]["y"] > 16:
                        owner_phone += candi["description"]

            elif (_json["description"].lower() == "#" and json_info[i + 1]["description"].lower() == "occupants") or \
                    ("#" in _json["description"].lower() and "occupants" in _json["description"].lower()):
                if _json["description"].lower() == "#" and json_info[i + 1]["description"].lower() == "occupants":
                    occupants_candidates, left, right, top, bottom = self.get_json_candidates(json_info=json_info,
                                                                                              f_json=_json,
                                                                                              s_json=json_info[i + 1],
                                                                                              diff_left_width=5,
                                                                                              diff_right_width=10)
                    left = max(left, _json["boundingPoly"]["vertices"][0]["x"] - 20)
                    right = min(right, json_info[i + 1]["boundingPoly"]["vertices"][1]["x"] + 20)
                else:
                    occupants_candidates, left, right, top, bottom = self.get_json_candidates(json_info=json_info,
                                                                                              f_json=_json,
                                                                                              s_json=_json,
                                                                                              diff_left_width=5,
                                                                                              diff_right_width=10)
                    left = max(left, _json["boundingPoly"]["vertices"][0]["x"] - 20)
                    right = min(right, _json["boundingPoly"]["vertices"][1]["x"] + 20)

                for candi in occupants_candidates:
                    if left <= 0.5 * (candi["boundingPoly"]["vertices"][0]["x"] +
                                      candi["boundingPoly"]["vertices"][1]["x"]) <= right and \
                            candi["boundingPoly"]["vertices"][3]["y"] - candi["boundingPoly"]["vertices"][0]["y"] > 16:
                        if candi["description"].isdigit():
                            occupants += candi["description"]
                occupants = occupants.replace("L", "")
                if occupants == "":
                    occupants = extract_digit_roi(roi_frame=frame[top:bottom, left:right])

            elif _json["description"].lower() == "damage" and json_info[i + 1]["description"].lower() == "scale":
                json_width = _json["boundingPoly"]["vertices"][0]["x"] - int(0.64 * frame_width)
                damage_scale_candidates, left, right, top, bottom = self.get_json_candidates(json_info=json_info,
                                                                                             f_json=_json,
                                                                                             s_json=json_info[i + 1],
                                                                                             diff_left_width=json_width)
                json_height = abs(_json["boundingPoly"]["vertices"][0]["y"] -
                                  _json["boundingPoly"]["vertices"][3]["y"])
                for j, candi in enumerate(damage_scale_candidates):
                    if candi["boundingPoly"]["vertices"][0]["x"] < _json["boundingPoly"]["vertices"][0]["x"]:
                        if candi["description"].replace(",", "").replace(".", "").isdigit():
                            if j < len(damage_scale_candidates) - 1:
                                if "-" not in candi["description"] and \
                                        damage_scale_candidates[j + 1]["description"] != "-":
                                    damage_scale += candi["description"]
                            else:
                                if "-" not in candi["description"]:
                                    damage_scale += candi["description"]
                if damage_scale == "":
                    damage_scale = extract_digit_roi(roi_frame=frame[top:bottom, left:right], base_height=json_height,
                                                     base_line_x=_json["boundingPoly"]["vertices"][0]["x"])
                if len(damage_scale) != 1:
                    if damage_scale == "11":
                        damage_scale = "1"
                    else:
                        damage_scale = damage_scale.replace("1", "")

            elif _json["description"].lower() == "insurance" and json_info[i + 1]["description"].lower() == "company":
                json_width = _json["boundingPoly"]["vertices"][1]["x"] - \
                             _json["boundingPoly"]["vertices"][0]["x"]
                insurance_company_candidates, _, _, _, _ = self.get_json_candidates(json_info=json_info, f_json=_json,
                                                                                    s_json=json_info[i + 1],
                                                                                    diff_right_width=json_width,
                                                                                    diff_left_width=5,
                                                                                    diff_bottom_height=40)
                for candi in insurance_company_candidates:
                    insurance_company += candi["description"] + " "

            elif _json["description"].lower() in ["insurance", "insyrance"] and \
                    json_info[i + 1]["description"].lower() == "policy":
                json_width = json_info[i + 3]["boundingPoly"]["vertices"][0]["x"] - \
                             json_info[i + 2]["boundingPoly"]["vertices"][1]["x"] - 20
                insurance_policy_candidates, _, _, _, _ = self.get_json_candidates(json_info=json_info, f_json=_json,
                                                                                   s_json=json_info[i + 1],
                                                                                   diff_left_width=5,
                                                                                   diff_right_width=json_width,
                                                                                   diff_bottom_height=40)
                for candi in insurance_policy_candidates:
                    policy_number += candi["description"] + " "

            elif _json["description"].lower() == "vehicle" and json_info[i + 1]["description"].lower() == "year":
                vehicle_year_candidates, _, _, _, _ = self.get_json_candidates(json_info=json_info, f_json=_json,
                                                                               s_json=json_info[i + 1],
                                                                               diff_left_width=5,
                                                                               diff_right_width=5,
                                                                               diff_bottom_height=40)
                for candi in vehicle_year_candidates:
                    if candi["description"].replace(",", "").replace(".", "").isdigit():
                        vehicle_year += candi["description"]

            elif _json["description"].lower() == "vehicle" and json_info[i + 1]["description"].lower() == "make":
                json_width = int(0.64 * frame_width) - json_info[i + 1]["boundingPoly"]["vertices"][1]["x"] - 5
                vehicle_make_candidates, _, _, _, _ = self.get_json_candidates(json_info=json_info, f_json=_json,
                                                                               s_json=json_info[i + 1],
                                                                               diff_left_width=10,
                                                                               diff_right_width=json_width)
                for candi in vehicle_make_candidates:
                    if not candi["description"].replace(",", "").replace(".", "").isdigit():
                        vehicle_make += candi["description"]

            elif _json["description"].lower() == "vehicle" and json_info[i + 1]["description"].lower() == "model":
                vehicle_model_candidates, _, _, _, _ = self.get_json_candidates(json_info=json_info, f_json=_json,
                                                                                s_json=json_info[i + 1],
                                                                                diff_left_width=5,
                                                                                diff_right_width=5)
                for candi in vehicle_model_candidates:
                    if _json["boundingPoly"]["vertices"][0]["x"] - 30 <= candi["boundingPoly"]["vertices"][0]["x"]:
                        vehicle_model += candi["description"]

            elif _json["description"].lower() == "unit" and json_info[i + 1]["description"].lower() == "type":
                unit_type_left = _json["boundingPoly"]["vertices"][0]["x"]
                unit_type_right = json_info[i + 1]["boundingPoly"]["vertices"][1]["x"]
                unit_type_top = _json["boundingPoly"]["vertices"][0]["y"] - 70
                unit_type_bottom = _json["boundingPoly"]["vertices"][0]["y"]
                unit_type_candidate = ""
                for _j_info in json_info:
                    if unit_type_left <= 0.5 * (_j_info["boundingPoly"]["vertices"][0]["x"] +
                                                _j_info["boundingPoly"]["vertices"][1]["x"]) <= unit_type_right and \
                            unit_type_top <= 0.5 * (_j_info["boundingPoly"]["vertices"][0]["y"] +
                                                    _j_info["boundingPoly"]["vertices"][3]["y"]) <= unit_type_bottom:
                        unit_type_candidate += _j_info["description"]

                for c_unit_type in unit_type_candidate:
                    if c_unit_type.isdigit():
                        unit_type += c_unit_type

                if unit_type == "":
                    unit_type = extract_digit_roi(roi_frame=frame[unit_type_top:unit_type_bottom,
                                                                  unit_type_left:unit_type_right])
                    # cv2.imshow("unit type", frame[unit_type_top:unit_type_bottom, unit_type_left:unit_type_right])
                    # cv2.waitKey()

        return unit_number, owner_name, owner_address, owner_phone, occupants, damage_scale, insurance_company, \
               policy_number, vehicle_year, vehicle_make, vehicle_model, unit_type

    def extract_motorist_occupant_page(self, json_info, frame_path):

        info = {}

        unit_number = ""
        owner_name = ""
        birth_date = ""
        age = ""
        gender = ""
        address = ""
        phone = ""
        injuries = ""
        seating_position = ""

        frame = cv2.imread(frame_path)
        frame_height, frame_width = frame.shape[:2]

        unit_cnt = 0
        sorted_json_info = sorted(json_info, key=lambda k: k["boundingPoly"]["vertices"][0]["y"])

        for i, _json in enumerate(sorted_json_info):
            unit_center_x = 0.5 * (_json["boundingPoly"]["vertices"][0]["x"] +
                                   _json["boundingPoly"]["vertices"][1]["x"])
            unit_center_y = 0.5 * (_json["boundingPoly"]["vertices"][0]["y"] +
                                   _json["boundingPoly"]["vertices"][3]["y"])
            if _json["description"].lower() == "unit" and unit_center_x < 0.15 * frame_width and \
                    unit_center_y < 0.5 * frame_height:
                unit_number_candidates, left, right, top, bottom = self.get_json_candidates(json_info=sorted_json_info,
                                                                                            f_json=_json,
                                                                                            s_json=_json)
                for candi in unit_number_candidates:
                    if candi["boundingPoly"]["vertices"][1]["x"] < \
                            sorted_json_info[i + 1]["boundingPoly"]["vertices"][1]["x"] + 30 \
                            and candi["description"].replace(",", "").replace(".", "").isdigit():
                        unit_number += candi["description"]
                if unit_number == "" or unit_number == "0":
                    unit_number = extract_digit_roi(roi_frame=frame[top:bottom, left + 15:right - 15])
                if unit_number != "":
                    unit_cnt += 1
                    if unit_number == "0":
                        unit_number += str(unit_cnt)
                    info[f"unit_{unit_cnt}"] = {}
                    info[f"unit_{unit_cnt}"]["unit_number"] = unit_number.replace(",", "").replace(".", "")
                    unit_number = ""

        if unit_cnt > 0:
            cnt = 1
            for i, _json in enumerate(sorted_json_info):
                if _json["description"].lower() == "name" and sorted_json_info[i + 2]["description"].lower() == "last":
                    json_width = int(0.64 * frame_width) - \
                                 sorted_json_info[i + 2]["boundingPoly"]["vertices"][1]["x"] - 5
                    owner_name_candidates, _, _, _, _ = self.get_json_candidates(json_info=sorted_json_info,
                                                                                 f_json=_json,
                                                                                 s_json=sorted_json_info[i + 1],
                                                                                 diff_bottom_height=40,
                                                                                 diff_left_width=5,
                                                                                 diff_right_width=json_width)

                    sorted_owner_name_candidates = sorted(owner_name_candidates,
                                                          key=lambda k: k["boundingPoly"]["vertices"][0]["x"])

                    for candi in sorted_owner_name_candidates:
                        owner_name += candi["description"] + " "
                    info[f"unit_{cnt}"]["name"] = owner_name
                    owner_name = ""

                elif _json["description"].lower() == "date" and \
                        sorted_json_info[i + 2]["description"].lower() == "birth":
                    json_width = sorted_json_info[i + 2]["boundingPoly"]["vertices"][1]["x"] - \
                                 _json["boundingPoly"]["vertices"][0]["x"]
                    birth_date_candidates = self.perform_ocr_roi_frame(f_json=_json, s_json=sorted_json_info[i + 2],
                                                                       frame=frame,
                                                                       diff_width=json_width, diff_bottom=50)
                    # if unit_cnt < 1:
                    #     break
                    # if cnt == 0 or "birth_date" in info[f"unit_{cnt}"]:
                    #     cnt += 1

                    for candi in birth_date_candidates:
                        if candi["description"].lower() not in ["date", "of", "birth"]:
                            birth_date += candi["description"]
                    birth_date = birth_date.replace(",", "").replace(".", "").replace("|", "")
                    if len(birth_date) == 10:
                        birth_date = birth_date[:2] + "/" + birth_date[3:5] + "/" + birth_date[6:]
                    info[f"unit_{cnt}"]["birth_date"] = birth_date
                    birth_date = ""
                elif _json["description"].lower() == "age":
                    json_width = _json["boundingPoly"]["vertices"][1]["x"] - _json["boundingPoly"]["vertices"][0]["x"]
                    age_candidates = self.perform_ocr_roi_frame(frame=frame, f_json=_json, s_json=_json,
                                                                diff_width=json_width)
                    for candi in age_candidates:
                        if candi["description"].lower() != "age":
                            age += candi["description"]

                    info[f"unit_{cnt}"]["age"] = age.replace(",", "").replace(".", "")
                    age = ""

                elif _json["description"].lower() == "gender":
                    gender_candidates = self.perform_ocr_roi_frame(frame=frame, f_json=_json, s_json=_json,
                                                                   diff_width=7)
                    for candi in gender_candidates:
                        if candi["description"].lower() not in ["gender", "gende"]:
                            gender += candi["description"]
                    info[f"unit_{cnt}"]["gender"] = gender.replace(",", "").replace(".", "")
                    gender = ""

                elif _json["description"].lower() == "address" and \
                        sorted_json_info[i + 1]["description"].lower() == ":":
                    json_width = int(0.64 * frame_width) - \
                                 sorted_json_info[i + 1]["boundingPoly"]["vertices"][1]["x"] - 5
                    address_candidates, _, _, _, _ = self.get_json_candidates(json_info=sorted_json_info, f_json=_json,
                                                                              s_json=sorted_json_info[i + 1],
                                                                              diff_right_width=json_width,
                                                                              diff_left_width=5)

                    for candi in address_candidates:
                        address += candi["description"] + " "
                    info[f"unit_{cnt}"]["address"] = address.replace(",", "").replace(".", "")
                    address = ""

                elif _json["description"].lower() == "contact" and \
                        sorted_json_info[i + 1]["description"].lower() == "phone":
                    phone_candidates, _, _, _, _ = self.get_json_candidates(json_info=sorted_json_info, f_json=_json,
                                                                            s_json=sorted_json_info[i + 1],
                                                                            diff_left_width=5)

                    for j, candi in enumerate(phone_candidates):
                        if candi["boundingPoly"]["vertices"][1]["x"] - candi["boundingPoly"]["vertices"][0]["x"] > 2:
                            phone += candi["description"]
                    info[f"unit_{cnt}"]["phone"] = phone.replace(",", "").replace(".", "")
                    phone = ""

                elif _json["description"].lower() == "injuries":
                    injuries_company_candidates, left, right, top, bottom = \
                        self.get_json_candidates(json_info=sorted_json_info, f_json=_json, s_json=_json,
                                                 diff_right_width=5)
                    for candi in injuries_company_candidates:
                        injuries += candi["description"] + " "
                    if injuries == "":
                        injuries = extract_digit_roi(roi_frame=frame[top:bottom, left:right])
                    info[f"unit_{cnt}"]["injuries"] = injuries.replace(",", "").replace(".", "")
                    injuries = ""
                    if "seating_position" in list(info[f"unit_{cnt}"].keys()):
                        if cnt == unit_cnt:
                            break
                        cnt += 1

                elif _json["description"].lower() == "seating" and \
                        sorted_json_info[i + 1]["description"].lower() == "position":
                    seating_position_candidates, left, right, top, bottom = \
                        self.get_json_candidates(json_info=sorted_json_info, f_json=_json,
                                                 s_json=sorted_json_info[i + 1],
                                                 diff_left_width=5, diff_right_width=5)
                    left = max(left, _json["boundingPoly"]["vertices"][0]["x"] - 3)
                    if right == 0:
                        right = sorted_json_info[i + 1]["boundingPoly"]["vertices"][1]["x"] + 3
                    else:
                        right = min(right, sorted_json_info[i + 1]["boundingPoly"]["vertices"][1]["x"] + 3)
                    for candi in seating_position_candidates:
                        if left <= 0.5 * (candi["boundingPoly"]["vertices"][0]["x"] +
                                          candi["boundingPoly"]["vertices"][1]["x"]) <= right:
                            seating_position += candi["description"]
                    if seating_position == "":
                        seating_position = extract_digit_roi(roi_frame=frame[top:bottom, left:right])
                    info[f"unit_{cnt}"]["seating_position"] = seating_position.replace(",", "").replace(".", "")
                    seating_position = ""
                    if "injuries" in list(info[f"unit_{cnt}"].keys()):
                        if cnt == unit_cnt:
                            break
                        cnt += 1

        del_keys = []
        for i_key in info.keys():
            try:
                if info[i_key]["name"] == "" and info[i_key]["birth_date"] == "":
                    del_keys.append(i_key)
            except Exception as e:
                del_keys.append(i_key)
                log_print(e)

        for d_key in del_keys:
            info.pop(d_key, None)

        return info

    def extract_page_info(self, pdf_page_frame_path, file_name=None, index=None, ocr_result=None):
        if os.path.exists(os.path.join(CUR_DIR, 'test_json', f"temp_{file_name}_{index}.json")):
            with open(os.path.join(CUR_DIR, 'test_json', f"temp_{file_name}_{index}.json")) as f:
                ocr_result = json.load(f)
        if ocr_result is None:
            ocr_result = self.ocr_tool.detect_text(img_path=pdf_page_frame_path)
            if LOCAL:
                json_file_path = os.path.join(CUR_DIR, 'test_json', f"temp_{file_name}_{index}.json")
                save_file(filename=json_file_path, content=json.dumps(ocr_result), method="w")

        pdf_page_frame = cv2.imread(pdf_page_frame_path)
        height, width = pdf_page_frame.shape[:2]
        page_title_frame = pdf_page_frame[:int(height / 8), :]
        title_frame_path = os.path.join(CUR_DIR, 'title.jpg')
        cv2.imwrite(title_frame_path, page_title_frame)

        title_ocr = self.ocr_tool.detect_text(img_path=title_frame_path)
        title_json = title_ocr["textAnnotations"][1:]
        needed_ocr = ocr_result["textAnnotations"][1:]
        self.box_row_lines, self.box_col_lines = extract_box_lines(frame_path=pdf_page_frame_path,
                                                                   json_info=needed_ocr)

        for j, pdf_json in enumerate(title_json):
            if pdf_json["description"].lower() == "ncic":
                if not self.report_page_ret:
                    report_number, crash_date_time, crash_severity, county, ncic, agency, units, unit_error = \
                        self.extract_report_page(json_info=needed_ocr, frame_path=pdf_page_frame_path)
                    # min_dist = needed_ocr[0]["boundingPoly"]["vertices"][0]["x"] + \
                    #            needed_ocr[0]["boundingPoly"]["vertices"][0]["y"]
                    # state = needed_ocr[0]["description"]
                    # for _json in needed_ocr[1:]:
                    #     dist = _json["boundingPoly"]["vertices"][0]["x"] + _json["boundingPoly"]["vertices"][0]["y"]
                    #     if dist < min_dist:
                    #         min_dist = dist
                    #         state = _json["description"]
                    # self.pdf_info["report"]["state"] = state
                    county = str(county).replace(",", "").replace(".", "")
                    if len(county) > 2:
                        county = county[:2]
                    self.pdf_info["report"]["report_number"] = \
                        str(report_number).replace(",", "").replace(".", "").replace(":", "")
                    self.pdf_info["report"]["crash_date_time"] = \
                        str(crash_date_time).replace(",", "").replace(".", "").replace(":", "")
                    # self.pdf_info["report"]["crash_date"] = str(crash_date)
                    # self.pdf_info["report"]["crash_time"] = str(crash_time)
                    self.pdf_info["report"]["county"] = county
                    self.pdf_info["report"]["agency_ncic"] = \
                        str(ncic).replace(",", "").replace(".", "").replace(":", "")
                    self.pdf_info["report"]["agency"] = str(agency).replace(",", "").replace(".", "").replace(":", "")
                    self.pdf_info["report"]["number_of_unit"] = \
                        str(units).replace(",", "").replace(".", "").replace(":", "")
                    self.pdf_info["report"]["unit_in_error"] = \
                        str(unit_error).replace(",", "").replace(".", "").replace(":", "")
                    self.pdf_info["report"]["crash_severity"] = \
                        str(crash_severity).replace(",", "").replace(".", "").replace(":", "")
                    self.report_page_ret = True
                    break
            elif pdf_json["description"].lower() == "unit" and abs(pdf_json["boundingPoly"]["vertices"][0]["y"] -
                                                                   pdf_json["boundingPoly"]["vertices"][3]["y"]) > 30:
                temp_dict = {}
                unit_number, owner_name, owner_address, owner_phone, occupants, damage_scale, insurance_company, \
                    policy_number, year, make, model, unit_type = \
                    self.extract_unit_page(json_info=needed_ocr, frame_path=pdf_page_frame_path)
                temp_dict["unit_number"] = unit_number.replace(",", "").replace(".", "").replace(":", "")
                temp_dict["owner_name"] = owner_name.replace(",", "").replace(".", "").replace(":", "")
                temp_dict["owner_address"] = owner_address.replace(",", "").replace(".", "").replace(":", "")
                temp_dict["owner_phone"] = owner_phone.replace(",", "").replace(".", "").replace(":", "")
                temp_dict["number_of_occupants"] = occupants.replace(",", "").replace(".", "").replace(":", "")
                temp_dict["damage_scale"] = damage_scale.replace(",", "").replace(".", "").replace(":", "")
                temp_dict["insurance_company"] = insurance_company.replace(",", "").replace(".", "").replace(":", "")
                temp_dict["policy_number"] = policy_number.replace(",", "").replace(".", "").replace(":", "")
                temp_dict["year"] = year.replace(",", "").replace(".", "").replace(":", "")[-4:]
                temp_dict["make"] = make.replace(",", "").replace(".", "").replace(":", "")
                temp_dict["model"] = model.replace(",", "").replace(".", "").replace(":", "")
                temp_dict["unit_type"] = unit_type.replace(",", "").replace(".", "").replace(":", "")
                blank_page = True
                for t_key in temp_dict.keys():
                    if temp_dict[t_key] != "":
                        blank_page = False
                        break
                if not blank_page:
                    self.pdf_info["unit"].append(temp_dict)
                break
            elif pdf_json["description"].lower() == "motorist" or pdf_json["description"].lower() == "occupant":
                info = self.extract_motorist_occupant_page(json_info=needed_ocr, frame_path=pdf_page_frame_path)
                if pdf_json["description"].lower() == "motorist":
                    self.pdf_info["motorist"] = info
                else:
                    self.pdf_info["occupant"] = info
                break

        os.remove(title_frame_path)

        return self.pdf_info

    def main(self, pdf_path):
        self.pdf_info = {"report": {}, "unit": [], "motorist": {}, "occupant": {}}
        pdf_images = [np.array(page) for page in convert_from_path(pdf_path, 200)]
        file_name = ntpath.basename(pdf_path).replace(".pdf", "")
        for i, pdf_image in enumerate(pdf_images):
            try:
                pdf_frame_path = os.path.join(PDF_IMAGES_DIR, f"{file_name}_{i}.jpg")
                cv2.imwrite(pdf_frame_path, pdf_image)
                self.pdf_info = self.extract_page_info(pdf_page_frame_path=pdf_frame_path, file_name=file_name, index=i)
            except Exception as e:
                print(e)
                log_print(e)

        for info_key in self.pdf_info.keys():
            if "report_number" in self.pdf_info["report"].keys():
                if info_key == "unit":
                    for unit_info in self.pdf_info[info_key]:
                        unit_info["report_number"] = self.pdf_info["report"]["report_number"]
                elif info_key in ["motorist", "occupant"]:
                    if "unit_1" in self.pdf_info[info_key].keys():
                        self.pdf_info[info_key]["unit_1"]["report_number"] = self.pdf_info["report"]["report_number"]

        return self.pdf_info


if __name__ == '__main__':
    # with open(
    #         '') as f:
    #     json_content_ = json.load(f)
    # PDFExtractor().extract_page_info(
    #     pdf_page_frame_path="",
    #     file_name="", index=4
    #     )
    import glob
    from src.pdf.creator import PDFCreator
    pdf_creator = PDFCreator()
    pdfs = glob.glob(os.path.join("/media/main/Data/Task/ScannedPDFOCR/Fwd__errors/input-files", "*.pdf"))
    for p_index, pdf_path_ in enumerate(pdfs):
        info_ = PDFExtractor().main(
            pdf_path=pdf_path_)
        pdf_creator.repopulate_pdf(info=info_, pdf_name=f"{ntpath.basename(pdf_path_).replace('.pdf', '')}.pdf")
