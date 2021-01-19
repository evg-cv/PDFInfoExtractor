import pytesseract
import cv2
import numpy as np
import configparser

from settings import CONFIG_FILE

params = configparser.ConfigParser()
params.read(CONFIG_FILE)
if params.get("DEFAULT", "windows_usage").lower() == "true":
    pytesseract.pytesseract.tesseract_cmd = params.get("DEFAULT", "tesseract_path")


def get_digit_from_ocr(rects, height, base_line_x, base_height):

    digit = ""
    for rect in rects.splitlines():
        box = rect.split(' ')
        character = box[0]
        x1 = int(box[1])
        y1 = height - int(box[4])
        y2 = height - int(box[2])
        character_height = abs(y2 - y1)
        if character.lower() == "o":
            character = "0"
        if character.isdigit():
            if base_line_x is not None:
                if x1 < base_line_x:
                    if character_height > base_height:
                        digit += character
            else:
                digit += character

    return digit


def extract_digit_roi(roi_frame, base_line_x=None, base_height=None):

    h, w = roi_frame.shape[:2]
    gray_img = cv2.cvtColor(roi_frame, cv2.COLOR_BGR2GRAY)
    # _, thresh_img = cv2.threshold(gray_img, 180, 255, cv2.THRESH_BINARY)
    dilate_img = cv2.dilate(gray_img, kernel=np.ones((2, 2), np.uint8), iterations=1)
    # cv2.imshow("thresh image", dilate_img)
    # cv2.waitKey()

    digit = perform_ocr(frame=dilate_img, base_height=base_height, base_line_x=base_line_x, height=h)
    if digit == "":
        digit = perform_ocr(frame=gray_img, base_height=base_height, base_line_x=base_line_x, height=h)

    return digit


def perform_ocr(frame, base_height, base_line_x, height):
    config = r'-l eng --oem 3 --psm 11'
    rects = pytesseract.pytesseract.image_to_boxes(image=frame, config=config)
    digit = get_digit_from_ocr(rects=rects, base_height=base_height, base_line_x=base_line_x, height=height)
    if digit == "":
        config = r'-l eng --oem 3 --psm 6'
        rects = pytesseract.pytesseract.image_to_boxes(image=frame, config=config)
        digit = get_digit_from_ocr(rects=rects, base_height=base_height, base_line_x=base_line_x, height=height)

    return digit


if __name__ == '__main__':
    extract_digit_roi(
        roi_frame=cv2.imread(""),
        base_line_x=200, base_height=12)
