import pandas as pd
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage
import re
import os

# input and output files
INPUT_FILE = os.getenv("INPUT_FILE", "transformation_files/Transformation_logic.xlsx")
OUTPUT_FILE = os.getenv("OUTPUT_FILE", "transformation_files/transformed_with_sql.xlsx")


#LLM as Ollama
llm = ChatOllama(model="gemma3:4b",temperature=0)


# building prompts as per requirement 
def build_prompt(row, multi_fields=None, exploded_alias=None):
    """
    exploded_alias: str or None. If source array exploded but target is scalar.
    multiple_fields: list of dict rows for struct/array combination
    """
    if multi_fields:
        source_cols = ", ".join(f"{r['source_column']}" for r in multi_fields)
        sub_cols = ", ".join(f"{r['source_sub_column']}" for r in multi_fields)
        transformation_logic = "; ".join(
            f"{r['transformation_logic']} AS {r['target_sub_column']}" if pd.notna(r['transformation_logic']) and str(r['transformation_logic']).strip() != "" 
            else f"{r['source_column']} AS {r['target_sub_column']}"
            for r in multi_fields
        )
        prompt_text = f"""
        You are a senior data engineer.
        Generate ONLY the SQL expression (not a full query) for the following array target.

        Combine the following source columns into a single array/struct:
        - source columns: {source_cols}
        - sub-columns: {sub_cols}
        - transformation logic: {transformation_logic}

        Rules:
        - Use only Apache Spark SQL / Databricks SQL functions
        - String, numeric, and boolean constants MUST be written as SQL literals
          (e.g. 'ABC', 123, true). **NEVER use lit()**
        - For direct mapping (no transformation), always use: source_sub_column AS target_column. Do NOT swap or modify these names.
        - Use struct() to combine multiple sub-columns
        - If target data type is array, wrap the struct() in ARRAY(...), e.g. ARRAY(STRUCT(...))
        - If the target data type and source data type are both scalar, strictly do NOT wrap the expression in STRUCT() or ARRAY(). Just generate the transformation logic
        - Direct mapping from source column or source sub column to target if transformation is empty. Strictly follow this example pattern: source column as target column. For example: customer_id as cust_id should remain same
        - Use CASE WHEN only if conditional logic exists
        - If any source column is an array, use the exploded alias {exploded_alias} in the expression
        - Strictly DO NOT use SELECT, FROM, EXPLODE(), ARRAY_ELEMENT_AT(), lit, or any other non-Spark SQL functions
        - Alias output as the target column only using AS
        - Return EXACTLY the expression, nothing else, no extra text, and strictly no SQL clause like SELECT or FROM table name
        - Strictly no SQL clause like SELECT or FROM table name or any other SQL clause inside ARRAY(....)
        """
    else:
        source_column_ref = row['source_column']
        # Using exploded_alias if source is an array and target is scalar
        if exploded_alias:
            source_column_ref = f"{exploded_alias}.{row['source_sub_column'] or row['source_column']}"

        # If transformation_logic is empty, direct mapping from source to target
        if pd.isna(row['transformation_logic']) or str(row['transformation_logic']).strip() == "":
            return f"{source_column_ref} AS {row['target_sub_column'] or row['target_column']}"

        prompt_text = f"""
        You are a senior data engineer.
        Generate ONLY the SQL expression (not a full query) for this field.

        Source:
        - column: {source_column_ref}
        - sub column: {row['source_sub_column']}
        - data type: {row['source_data_type']}
        - sub data type: {row['source_sub_data_type']}

        Transformation logic:
        {row['transformation_logic']}

        Target:
        - column: {row['target_column']}
        - sub column: {row['target_sub_column']}
        - data type: {row['target_data_type']}
        - sub data type: {row['target_sub_data_type']}

        Rules:
        - Use only Apache Spark SQL / Databricks SQL functions
        - String, numeric, and boolean constants MUST be written as SQL literals
          (e.g. 'ABC', 123, true). **NEVER use lit()**
        - Never use aggregate functions like sum unless explicitly mentioned so
        - Never wrap in struct() or in array() if target data type is not array
        - If the target data type is SCALAR like string, int, etc, strictly alias the output using AS {row['target_column']}
        - Use struct() if combining multiple sub-columns and only if target data type is array
        - Only if target data type is array, wrap the struct() in ARRAY(...), e.g. ARRAY(STRUCT(...))
        - If the target data type and source data type are both scalar, strictly do NOT wrap the expression in STRUCT() or ARRAY(). Just generate the transformation logic and alias it as the target column
        - Direct mapping from source column or source sub column to target if transformation is empty
        - Use CASE WHEN only if conditional logic exists
        - Use exploded alias {exploded_alias} if source is array but target is scalar
        - Alias output only with AS
        - Return EXACTLY the expression, nothing else, no extra text, and strictly no SQL clause like SELECT or FROM table name
        - Strictly no SQL clause like SELECT or FROM table name or any other SQL clause inside ARRAY(....)
        """
    return prompt_text


def main():
    # MAIN
    df = pd.read_excel(INPUT_FILE) # read from an excel file

    # copy
    df = df.copy()

    # output columns
    df['generated_sql_expression'] = "" # to store generated sqls
    df['lateral_exploded_alias'] = ""  # to store exploded alias along with lateral view explode clause if source is an array but target is scalar

    # list of source_sub _column_fields; prepared so that transformation logic can be modified
    array_fields = []
    for idx, row in df.iterrows():
        if row['source_data_type'] == 'array':
            exploded_alias_name = f"{row['source_column'][:3]}_{row['source_column'][-3:]}_expl"
            sub_col = row['source_sub_column']
            target_table=row['target_table']
            array_fields.append((exploded_alias_name, sub_col, target_table))


    # For array aggregation need to group by target table and target column
    grouped = df.groupby(['target_table', 'target_column'])

    for (_, _), group in grouped:
        # target is an array with multiple sub-columns; first case
        if group['target_data_type'].iloc[0] == 'array' and len(group) > 1:
            prompt = build_prompt(None, multi_fields=group.to_dict('records'))
            response = llm.invoke([HumanMessage(content=prompt)])
            expr = response.content.replace("```", "").replace("sql", "").replace("`","").strip()
            df.loc[group.index[0], 'generated_sql_expression'] = expr
            continue
        
        # scalar target
        for idx, row in group.iterrows():
            # no mapping if target_column is not present
            if pd.isna(row['target_column']):
                continue

            # source is an array but target is not an array (exploded_alias is needed in that case)
            exploded_alias_name = None
            
            if row['source_data_type'] == 'array' and row['target_data_type'] != 'array':
                source_col = str(row['source_column'])
                exploded_alias_name = f"{source_col[:3]}_{source_col[-3:]}_expl"
                df.at[idx, 'lateral_exploded_alias'] = f"LATERAL VIEW EXPLODE({source_col}) AS {exploded_alias_name}"

                # --- Updated logic: replace references in transformation_logic ---
                if pd.notna(row['transformation_logic']) and str(row['transformation_logic']).strip() != "":
                    for alias, sub_col, tgt_table in array_fields:
                        # target table needs to be same to replace
                        if tgt_table == row['target_table'] and sub_col:
                            # Use word boundaries to avoid partial matches
                            row['transformation_logic'] = re.sub(
                                rf'\b{sub_col}\b', f"{alias}.{sub_col}", row['transformation_logic']
                            )
    
            # Direct mapping if transformation logic is empty
            if pd.isna(row['transformation_logic']) or str(row['transformation_logic']).strip() == "":
                source_ref = exploded_alias_name + "." + (row['source_sub_column'] or row['source_column']) if exploded_alias_name else row['source_column']
                df.at[idx, 'generated_sql_expression'] = f"{source_ref} AS {row['target_column']}"
                continue
            

            # Build prompt for LLM
            prompt = build_prompt(row, exploded_alias=exploded_alias_name)
            response = llm.invoke([HumanMessage(content=prompt)])
            expr = response.content.replace("```", "").replace("sql", "").replace("`","").strip()
            
            #if target is scalar as target column_name is must; added this if incase LLM, fails       
            if row['target_data_type'] != 'array' and not re.search(r'\s+AS\s+', expr, flags=re.IGNORECASE):
                expr += f" AS {row['target_column']}"

            df.at[idx, 'generated_sql_expression'] = expr

    #Saving output in an excel file
    df.to_excel(OUTPUT_FILE, index=False)
    print(f"SQL expressions written to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()