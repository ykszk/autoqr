# Q/R for DICOM
[![codecov](https://codecov.io/gh/yk-szk/autoqr/branch/master/graph/badge.svg)](https://codecov.io/gh/yk-szk/autoqr)

- Sequentially execute Q/R
- Scheduled execution (e.g. execute Q/R only during night-time)

## Run
```sh
python autoqr.py
```

## Scripts
- `range_query.py`: Query studies based on date range
- `study_query.py`: Query series by study instance UID
- `scripts/split_csv.py`: Split csv by the number of rows
- `scripts/concat_csv.py`: Concatenate multiple csv files
- `scripts/dcmsendall.py`: Useless since dcmsend has the same functionality.
- `scripts/remove_original.py`: Remove columns containing "original".

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
