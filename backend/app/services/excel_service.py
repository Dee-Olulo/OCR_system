# /backend/app/services/excel_service.py

import openpyxl

class ExcelService:
    def extract_text_from_excel(self, file_path: str) -> str:
        """Extract text from Excel file"""
        try:
            wb = openpyxl.load_workbook(file_path, data_only=True)
            full_text = []

            for sheet in wb.worksheets:
                full_text.append(f"Sheet: {sheet.title}")
                for row in sheet.iter_rows(values_only=True):
                    row_text = " | ".join(
                        str(cell) for cell in row if cell is not None
                    )
                    if row_text.strip():
                        full_text.append(row_text)

            return "\n".join(full_text)

        except Exception as e:
            print(f"Excel extraction error: {e}")
            return ""

excel_service = ExcelService()