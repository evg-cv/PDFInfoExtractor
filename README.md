# PDFInfoExtractor

## Overview

This project is to extract the necessary information from the scanned pdf files and upload it to AWS.
The main part of this project is to extract the necessary information from the whole text with the OCR technology
including the Tesseract framework and AWS Textract.

## Structure

- src

    The main source code for OCR, uploading, and image processing

- app

    The main execution file

- requirements

    All the dependencies for this project
    
- settings

    Several settings including files path and static values

## Installation

- Environment
    
    Ubuntu 18.04, Windows 10, Python 3.6

- Dependency Installation

    Please run the following command in this project directory in the terminal.
    ```
    pip3 install -r requirements.txt
    ```

## Execution

- Please run the following command in the terminal.

    ```
    python3 app.py
    ```

