FROM python:3.12

WORKDIR /workspaces/ETL_opgave_webshop

COPY data_processing_pipeline/requirements.txt ./data_processing_pipeline/
COPY data_processing_pipeline/requirements-dev.txt ./data_processing_pipeline/

COPY product_api/requirements.txt ./product_api/
COPY product_api/requirements-dev.txt ./product_api/

RUN pip install --no-cache-dir \
-r data_processing_pipeline/requirements-dev.txt \
-r product_api/requirements-dev.txt

CMD ["sleep", "infinity"]