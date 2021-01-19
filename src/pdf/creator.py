import os
import ntpath
import glob
import cv2
import img2pdf
import fitz

from settings import REPORT_TEXT_POSITION, UINT_TEXT_POSITION, MOTORIST_TEXT_POSITION, FONT_SIZE, FONT_WIDTH, \
    OUTPUT_DIR, SAMPLE_DIR, MOTORIST_SPACING, OCCUPANT_SPACING, SAMPLE_PDF


class PDFImageCreator:
    def __init__(self):
        self.pdf_pages = []

    @staticmethod
    def input_extracted_info(e_info, info_pos, frame_path, interval_spacing=0, index=0):
        frame = cv2.imread(frame_path)
        frame_name = ntpath.basename(frame_path)
        output_frame_path = os.path.join(OUTPUT_DIR, f"{frame_name.replace('.jpg', '')}_{index}.jpg")
        for e_key in e_info.keys():
            left, top = info_pos[e_key]
            top += interval_spacing
            text = e_info[e_key]
            cv2.putText(frame, str(text), (left, top), cv2.FONT_HERSHEY_SIMPLEX, FONT_SIZE, (0, 0, 0), FONT_WIDTH)

        cv2.imwrite(output_frame_path, frame)

        return output_frame_path

    def repopulate_pdf(self, info, pdf_name):
        output_images = glob.glob(os.path.join(OUTPUT_DIR, "*.jpg"))
        for output_image in output_images:
            os.remove(output_image)

        for f_key in info.keys():
            if f_key == "report":
                if bool(info[f_key]):
                    frame_path = os.path.join(SAMPLE_DIR, 'report.jpg')
                    report_frame_path = self.input_extracted_info(e_info=info[f_key], info_pos=REPORT_TEXT_POSITION,
                                                                  frame_path=frame_path)
                    self.pdf_pages.append(report_frame_path)
            elif f_key == "unit":
                if info[f_key]:
                    frame_path = os.path.join(SAMPLE_DIR, 'unit.jpg')
                    for i, unit_info in enumerate(info[f_key]):
                        unit_frame_path = self.input_extracted_info(e_info=unit_info, info_pos=UINT_TEXT_POSITION,
                                                                    frame_path=frame_path, index=i)
                        self.pdf_pages.append(unit_frame_path)
            elif f_key == "motorist" or f_key == "occupant":
                if bool(info[f_key]):
                    if f_key == "motorist":
                        motorist_occupant_frame_path = os.path.join(SAMPLE_DIR, 'motorist.jpg')
                        spacing = MOTORIST_SPACING
                    else:
                        motorist_occupant_frame_path = os.path.join(SAMPLE_DIR, 'occupant.jpg')
                        spacing = OCCUPANT_SPACING
                    for s_key in info[f_key].keys():
                        sub_index = int(s_key.replace("unit_", ""))
                        motorist_occupant_frame_path = \
                            self.input_extracted_info(e_info=info[f_key][s_key], info_pos=MOTORIST_TEXT_POSITION,
                                                      frame_path=motorist_occupant_frame_path,
                                                      interval_spacing=spacing * (sub_index - 1))
                    self.pdf_pages.append(motorist_occupant_frame_path)

        output_pdf_path = os.path.join(OUTPUT_DIR, pdf_name)
        with open(output_pdf_path, "wb") as f:
            f.write(img2pdf.convert(self.pdf_pages))

        self.pdf_pages = []

        print(f"Successfully saved {output_pdf_path}")

        return output_pdf_path


class PDFCreator:
    def __init__(self):
        self.pdf_docs = []

    @staticmethod
    def input_extracted_info(e_info, info_pos, pdf_path, interval_spacing=0, pdf_index=0):

        doc = fitz.open(pdf_path)
        pdf_name = ntpath.basename(pdf_path)

        for e_key in e_info.keys():
            left, top = info_pos[e_key]
            top += interval_spacing
            text = e_info[e_key]
            pos = fitz.Point(left, top)
            doc[0].insertText(pos, text, fontname="helv", fontsize=7, rotate=0)
        temp_pdf_doc_path = os.path.join(OUTPUT_DIR, f"temp_{pdf_name.replace('.pdf', '')}_{pdf_index}.pdf")
        doc.save(temp_pdf_doc_path)

        return temp_pdf_doc_path

    def repopulate_pdf(self, info, pdf_name):
        output_pdf_path = os.path.join(OUTPUT_DIR, pdf_name)

        for f_key in info.keys():
            if f_key == "report":
                if bool(info[f_key]):
                    pdf_path = os.path.join(SAMPLE_DIR, "report.pdf")
                    report_pdf_path = self.input_extracted_info(e_info=info[f_key], info_pos=REPORT_TEXT_POSITION,
                                                                pdf_path=pdf_path)
                    self.pdf_docs.append(report_pdf_path)

            elif f_key == "unit":
                if info[f_key]:
                    pdf_path = os.path.join(SAMPLE_DIR, 'unit.pdf')
                    for i, unit_info in enumerate(info[f_key]):
                        unit_pdf_path = self.input_extracted_info(e_info=unit_info, info_pos=UINT_TEXT_POSITION,
                                                                  pdf_path=pdf_path, pdf_index=i)
                        self.pdf_docs.append(unit_pdf_path)

            elif f_key == "motorist" or f_key == "occupant":
                if bool(info[f_key]):
                    if f_key == "motorist":
                        spacing = MOTORIST_SPACING
                        motorist_occupant_pdf_path = os.path.join(SAMPLE_DIR, "motorist.pdf")
                    else:
                        spacing = OCCUPANT_SPACING
                        motorist_occupant_pdf_path = os.path.join(SAMPLE_DIR, "occupant.pdf")
                    for s_key in info[f_key].keys():
                        sub_index = int(s_key.replace("unit_", ""))
                        motorist_occupant_pdf_path = \
                            self.input_extracted_info(e_info=info[f_key][s_key], info_pos=MOTORIST_TEXT_POSITION,
                                                      pdf_path=motorist_occupant_pdf_path,
                                                      interval_spacing=spacing * (sub_index - 1))
                    self.pdf_docs.append(motorist_occupant_pdf_path)

        result_doc = fitz.open()
        for p_doc in self.pdf_docs:
            infile = fitz.open(p_doc)
            last_page = len(infile) - 1
            result_doc.insertPDF(infile, from_page=last_page, to_page=last_page)
            infile.close()
        result_doc.save(output_pdf_path, deflate=True, garbage=3)

        for p_doc in self.pdf_docs:
            os.remove(p_doc)
        self.pdf_docs = []

        print(f"[INFO] Successfully saved {output_pdf_path}")

        return output_pdf_path


if __name__ == '__main__':
    from src.pdf.extractor import PDFExtractor

    info_ = PDFExtractor().main(pdf_path="")
    PDFCreator().repopulate_pdf(info=info_, pdf_name="1.pdf")
