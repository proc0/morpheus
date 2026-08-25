# Morpheus
Morpheus is an AI prototype in Morgan Everett's residence created sometime after 2027 by the collaboration of Morgan Everett and Bob Page.

# Requirements
 - Python 3.12+
 - uv
 - Ollama or AI Provider Account

# Run 
Clone and from the root directory:
```python
uv sync
```
Open a second terminal and run the piper server (voice):
```python
uv run -m piper.http_server -m assets/morpheus-medium.onnx --data-dir assets
```
Go back to the first terminal and run the main server:
```python
uv run src/morpheus/main.py
```
Open localhost:8000 in the browser.

