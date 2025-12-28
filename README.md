# ETL SQL Generator Docker Image

This Docker image contains a Python-based ETL SQL generator. It comes preloaded with a default input file (`Transformation_logic.xlsx`) so that users can immediately run transformations and generate output locally.  

The script now supports **environment variables** for input and output files, making it flexible when mounting folders in Docker.

---

## ✅ Features

- Preloaded `Transformation_logic.xlsx` file for easy testing.
- Generates SQL transformations based on the input file.
- Fully containerized with Docker; no need to install Python or dependencies locally.
- Supports custom input/output files via environment variables.
- Versioned Docker image (`latest` and `1.0.0`) for reproducibility.

---

## 📦 Pull the Docker Image

```bash
docker pull <YOUR_DOCKERHUB_USERNAME>/etl_sql_generator:latest
Replace <YOUR_DOCKERHUB_USERNAME> with your Docker Hub username.

🚀 Run the Container (Default Input)
By default, the container will use the included Transformation_logic.xlsx and output results to the container. You can mount a local folder to store the output:

bash
Copy code
docker run --rm -v /path/to/local/output:/app/output \
  <YOUR_DOCKERHUB_USERNAME>/etl_sql_generator:latest
Explanation:

--rm → Automatically removes the container after it finishes.

-v /path/to/local/output:/app/output → Mounts a local folder to /app/output inside the container so you can access generated files locally.

The default input file used inside the container is:

bash
Copy code
/app/transformation_files/Transformation_logic.xlsx
The default output file is:

bash
Copy code
/app/transformation_files/transformed_with_sql.xlsx
📝 Using Your Own Input File
If you want to use your own Transformation_logic.xlsx or change the output location:

Place your Excel file in a local folder, e.g., /path/to/local/input.

Mount it inside the container and set environment variables:

bash
Copy code
docker run --rm \
  -v /path/to/local/input:/app \
  -v /path/to/local/output:/app/output \
  -e INPUT_FILE="/app/Transformation_logic.xlsx" \
  -e OUTPUT_FILE="/app/output/transformed_with_sql.xlsx" \
  <YOUR_DOCKERHUB_USERNAME>/etl_sql_generator:latest
INPUT_FILE → path to your input Excel inside the container.

OUTPUT_FILE → path to write the generated SQL output.

⚡ Modify Input File
Open your Transformation_logic.xlsx in Excel or Google Sheets.

Edit or add transformation rules as needed.

Save the file and rerun the container using the steps above.

📂 Output
All generated SQL scripts or outputs will be saved in the folder you mounted as /app/output.

You can open these files directly on your local machine.

📌 Notes
The container uses Python 3.11 and all dependencies are pre-installed.

Make sure you have Docker installed and running locally.

By default, the container uses Transformation_logic.xlsx included in the image if no custom file is provided.

You can run the versioned image using:

bash
Copy code
docker pull <YOUR_DOCKERHUB_USERNAME>/etl_sql_generator:1.0.0
docker run --rm -v /path/to/local/output:/app/output \
  <YOUR_DOCKERHUB_USERNAME>/etl_sql_generator:1.0.0