# Model setup

Both models are optional. Without them the deterministic analysis still works and the UI shows each model as "unavailable".

## 1. Application

```bash
pip install -r requirements.txt
```

## 2. Gemma via Ollama (topic suggestions)

1. Install [Ollama](https://ollama.com) and review the Gemma licence.
2. Pull a model: `ollama pull gemma3:4b`.
3. Configure `.env`:

   ```
   OLLAMA_ENDPOINT=http://127.0.0.1:11434
   OLLAMA_MODEL=gemma3:4b
   ```

The model is downloaded once; afterwards inference runs locally.

## 3. TabPFN (backtest scoring)

1. Accept the licence at [platform.priorlabs.ai](https://platform.priorlabs.ai). Some TabPFN versions are non-commercial.
2. `pip install tabpfn`.
3. Complete Prior Labs' local weight-access setup. Never put tokens in source files. CPU is sufficient for small tables.

## 4. Verify

```bash
python scripts/verify_installation.py
python scripts/run_evaluation.py --version v2
```

The evaluation report states whether TabPFN actually ran. If a model is missing, results show "unavailable" and are never replaced by a substitute.
