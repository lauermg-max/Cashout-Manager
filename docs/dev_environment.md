# Development Environment Setup

## Virtual Environment and Dependencies
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

## Editable Install (Optional but Recommended)
Install the project in editable mode so the package can be imported without setting `PYTHONPATH` manually.
```bash
pip install -e .
```

Alternatively, set `PYTHONPATH` permanently for the current shell session:
```bash
set PYTHONPATH=%CD%\src       # Windows
export PYTHONPATH=$PWD/src     # macOS / Linux
```

## Running the Application
```bash
python -m gift_card_manager
# or
python src/gift_card_manager/app.py
```

## Static Checks
```bash
python -m compileall src
```
