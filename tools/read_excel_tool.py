from langchain.tools import tool
import pandas as pd
import math

@tool
def excel_tool(file_path: str) -> dict:  # return dict instead of list
    """
    Reads an Excel mapping file and returns a list of dictionaries,
    replacing NaN with None for JSON safety. Ensures all required columns exist.
    """
    df = pd.read_excel(file_path)
    # ... your existing processing ...
    records = []
    for row in df.to_dict(orient="records"):
        safe_row = {k: (None if (isinstance(v, float) and math.isnan(v)) else v)
                    for k, v in row.items()}
        records.append(safe_row)
    # Wrap in a dict
    return {"data": records}

