import json
import cv2
import numpy as np


def extract_box_lines(frame_path, json_info):
    frame = cv2.imread(frame_path)
    frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    for _json in json_info:
        left = _json["boundingPoly"]["vertices"][0]["x"]
        right = _json["boundingPoly"]["vertices"][1]["x"]
        top = _json["boundingPoly"]["vertices"][0]["y"]
        bottom = _json["boundingPoly"]["vertices"][3]["y"]
        cv2.rectangle(frame_gray, (left, top), (right, bottom), 255, -1)

    # cv2.imshow("non character frame", frame_gray)
    _, thresh_frame = cv2.threshold(frame_gray, 175, 255, cv2.THRESH_BINARY)
    dilate_frame = cv2.erode(thresh_frame, np.ones((2, 2), np.uint8), iterations=4)
    dilate_frame_inv = cv2.bitwise_not(dilate_frame)
    # cv2.imshow("frame inv", dilate_frame_inv)
    # cv2.waitKey()
    min_line_length = 30
    max_line_gap = 1
    lines = cv2.HoughLinesP(dilate_frame_inv, 1, np.pi / 180, 100, minLineLength=min_line_length,
                            maxLineGap=max_line_gap)
    row_lines = []
    col_lines = []
    for line in lines:
        x1, y1, x2, y2 = line[0]
        if abs(x1 - x2) > abs(y1 - y2):
            grad = (y1 - y2) / abs(x1 - x2)
            if grad > 0.1:
                continue
            row_lines.append([min(x1, x2), max(x1, x2), int(0.5 * (y1 + y2))])
        else:
            col_lines.append([min(y1, y2), max(y1, y2), int(0.5 * (x1 + x2))])

        cv2.line(frame, (x1, y1), (x2, y2), (0, 0, 255), 3)

    cv2.imwrite("t.jpg", frame)

    # cv2.imshow("line frame", cv2.resize(frame, (1080, 720)))
    # cv2.waitKey()
    return row_lines, col_lines


if __name__ == '__main__':
    with open('') as f:
        json_content_ = json.load(f)
    extract_box_lines(frame_path="",
                      json_info=json_content_["textAnnotations"][1:])
