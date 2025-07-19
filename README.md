# MicrobeLLM
A benchmark of LLMs for diet recommendations with Foods with Live Microbes (FLM)

# Table of Contents
- [Installation](#installation)
- [Preparation](#preparation)
- [Execution](#execution)

## Installation

- Clone the repository.
- Install dependencies using `requirements.txt`.
- Install [PostgreSQL](https://www.postgresql.org/)
- Run `pgAdmin`
- Install and run [Ollama](https://ollama.com/)
- From Ollama, use `ollama pull [model]` to download the desired model.

## Preparation

- Run `update_cnf.py` to update the CNF CSV files.
- Run `clean_conversion.py` to convert certain measure units with errors in CNF.
- Run `cnf-postgress.ipynb` to create the CNF tables. NOTE: This step assumes that PostgreSQL is installed and pgAdmin is running.

## Execution
- You can run `diet-llm.ipynb` for a simple LLM with no RAG or tools. This model can employ in-context or few-shot prompting.
- You can run `diet-rag.ipynb` for additional RAG and tools on top of in-context and few-shot prompting.
