from langchain.tools import tool
import os
import pandas as pd

# Base output directory
DATA_PATH = os.getenv("DATA_PATH", "transformation_files")
OUTPUT_FILE = "Transformed_file.xlsx"

@tool
def save_excel_tool(rows: list[dict]) -> str:
    """
    Save transformed rows to a fixed Excel file.
    """
    os.makedirs(DATA_PATH, exist_ok=True)
    output_file_path = os.path.join(DATA_PATH, OUTPUT_FILE)

    df = pd.DataFrame(rows)
    df.to_excel(output_file_path, index=False)

    return f"Excel saved to {output_file_path}"
