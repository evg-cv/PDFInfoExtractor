import ntpath
import threading
import glob
import os

from src.pdf.extractor import PDFExtractor
from src.pdf.creator import PDFCreator
from src.aws.s3_manager import S3Manager
from utils.folder_file_manager import save_file, log_print
from settings import INPUT_DIR, PROCESSED_FILE, OUTPUT_DIR, PDF_IMAGES_DIR


class PDFScanner:
    def __init__(self):
        self.pdf_extractor = PDFExtractor()
        self.pdf_creator = PDFCreator()
        self.s3_manager = S3Manager()
        self.processed_files = []
        print("[INFO] Initializing...")
        self.__initialize()

    @staticmethod
    def __init_directory(dir_path):
        file_list = glob.glob(os.path.join(dir_path, "*.*"))
        for file in file_list:
            os.remove(file)

    def __initialize(self):
        for dir_path in [INPUT_DIR, OUTPUT_DIR, PDF_IMAGES_DIR]:
            self.__init_directory(dir_path=dir_path)

        with open(PROCESSED_FILE, 'r') as f:
            self.processed_files = f.read().split("\n")

    def perform_ocr(self):
        # upload_files_len = len(glob.glob(os.path.join(OUTPUT_DIR, "*.pdf")))
        # download_files_len = len(glob.glob(os.path.join(INPUT_DIR, "*.pdf")))
        while True:
            input_files = glob.glob(os.path.join(INPUT_DIR, "*.*"))
            for pdf_path in input_files:
                try:
                    pdf_name = ntpath.basename(pdf_path)
                    extension = pdf_name[pdf_name.rfind(".") + 1:]
                    if extension != "pdf":
                        continue
                    if pdf_name not in self.processed_files:
                        print(f"[INFO] {pdf_name} processing...")
                        extracted_info = self.pdf_extractor.main(pdf_path=pdf_path)
                        output_pdf_path = self.pdf_creator.repopulate_pdf(info=extracted_info, pdf_name=pdf_name)
                        self.s3_manager.upload_files(file_path=output_pdf_path)
                        self.processed_files.append(pdf_name)
                except Exception as e:
                    log_print(e)
            # upload_files_len = len(glob.glob(os.path.join(OUTPUT_DIR, "*.pdf")))
            # download_files_len = len(glob.glob(os.path.join(INPUT_DIR, "*.pdf")))

            content = ""
            for i, file_name in enumerate(self.processed_files):
                if i < len(self.processed_files) - 1:
                    content += file_name + "\n"
                else:
                    content += file_name
            save_file(content=content, filename=PROCESSED_FILE, method='w')

    def run(self):
        download_thread = threading.Thread(target=self.s3_manager.download_files, args=[self.processed_files.copy(), ])
        download_thread.start()
        upload_thread = threading.Thread(target=self.perform_ocr, args=[])
        upload_thread.start()

        download_thread.join()
        upload_thread.join()


if __name__ == '__main__':
    PDFScanner().run()
