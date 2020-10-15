# Q/R for DICOM
[![codecov](https://codecov.io/gh/yk-szk/autoqr/branch/master/graph/badge.svg)](https://codecov.io/gh/yk-szk/autoqr)

- Sequentially execute Q/R
- Scheduled execution

## Run
```sh
python order_id.py
```

## Scripts
- `range_query.py`: Date range based query
- `study_query.py`: Query by study instance UID
- `scripts/split_csv.py`: Split csv by the number of rows
- `scripts/concat_csv.py`: Concatenate multiple csv files
- `scripts/dcmsendall.py`: Useless since dcmsend has the same functionality.

## Development

### Init
``` sh
# Install packages
pip install -r requirements.txt
# Pre-commit hooks
pre-commit install
```
### Test
``` sh
python -m pytest --cov tests
```
