# Real-data notebooks (KDD stages 1-5)

Machine learning on the two real weather files in the repo root
(`durban_kzn_daily_2021-2022.xlsx`, `mbombela_mpumalanga_daily_2021-2022.csv.xlsx`).
The notebooks are saved **with their outputs**, so they open fully rendered for a presentation.

| Notebook | Stage | What it does |
|---|---|---|
| `01_selection.ipynb` | Selection | Loads both files, checks coverage/integrity, plots rainfall, records SHA-256 checksums |
| `02_preprocessing.ipynb` | Preprocessing | Validates ranges, converts wind to m/s, documents why nothing is imputed or clipped |
| `03_transformation.ipynb` | Transformation | Builds features and the next-day heavy-rain target, chronological 60/20/20 split, train-only scaling |
| `04_data_mining.ipynb` | Data mining | Always-no and persistence baselines vs logistic regression, random forest, gradient boosting; hold-out, walk-forward and bootstrap evaluation |
| `05_interpretation.ipynb` | Interpretation | ROC/PR curves, confusion matrices, feature importance, April/May 2022 Durban case study, limits |

## Important
- The target is **next-day rainfall >= 10 mm**, not floods: these files contain no flood records, river levels or
  satellite tiles, so the backend CNN-LSTM cannot be trained on them. Do not report these scores as flood accuracy.
- On this data the simple persistence rule is at least as good as the learned models (see notebook 05, section 6).
- Outputs (cleaned data, features, metrics, predictions, figures) go to `outputs/`. `models/` is not touched.

## Run
Open the notebooks in Jupyter/VS Code (needs numpy, pandas, scikit-learn, matplotlib, openpyxl, joblib) and run top to
bottom, 01 to 05. To rebuild all five with fresh outputs without Jupyter: `python scripts/build_real_notebooks.py`
(edit the `src/*.py` files, not the .ipynb files).
