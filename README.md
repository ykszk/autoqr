# Q/R for DICOM

- Sequentially execute Q/R
- Scheduled execution


## Development

### Init
``` sh
# Install packages
pip install -r requirements.txt
# Ignore changes to .env file
git update-index --assume-unchanged config/.env
# Pre-commit hooks
pre-commit install
```
### Test
``` sh
python -m pytest --cov tests
```
