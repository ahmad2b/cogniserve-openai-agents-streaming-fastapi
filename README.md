# CogniServe

This is a starter template for a FastAPI project using `uv` as the package and environment manager.

## Getting Started

### Prerequisites

- [uv](https://github.com/astral-sh/uv)

### Setup

1.  Create and activate a virtual environment:
    ```bash
    uv venv
    source .venv/bin/activate
    # On Windows, use `.venv\Scripts\activate`
    ```

2.  Install dependencies:
    ```bash
    uv pip install -e .
    ```

### Running the application

To run the application, use `uvicorn`:

```bash
uvicorn cogniserve.main:app --reload
```

The application will be available at `http://127.0.0.1:8000`.

You can access the interactive API documentation at `http://127.0.0.1:8000/docs`.
