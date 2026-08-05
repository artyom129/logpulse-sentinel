.PHONY: install test seed run demo

install:
	python -m pip install -r requirements.txt

test:
	pytest -q

seed:
	python seed_demo.py

run:
	python run.py

demo:
	python scripts/generate_demo_log.py
