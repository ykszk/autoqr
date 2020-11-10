# Q/R for DICOM
[![codecov](https://codecov.io/gh/yk-szk/autoqr/branch/master/graph/badge.svg)](https://codecov.io/gh/yk-szk/autoqr)

- Sequentially execute Q/R
- Scheduled execution (e.g. execute Q/R only during night-time)

## Requirements
`movescu` from [dcmtk](https://dicom.offis.de/dcmtk.php.en)

## Run
```sh
python gui.py
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
# Packages for development
pip install freezegun
# Pre-commit hooks
pre-commit install
```
### Test all
``` sh
python -m pytest --cov tests
```

### Test single file
``` sh
python -m pytest tests/filename.py
```
Or `ctrl+shift+b` in vscode.

### Test on GitHub Actions
Include `[runtest]` keyword in the commit message.
