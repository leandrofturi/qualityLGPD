import numpy as np
import pandas as pd

import matplotlib.pyplot as plt
from sklearn.preprocessing import LabelEncoder
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    confusion_matrix,
    accuracy_score,
    plot_confusion_matrix,
    adjusted_rand_score,
    precision_recall_fscore_support,
)

# from cleaner.eleicoes import cleaner
from anonymization.supression import Supression
from anonymization.randomization import Randomization
from anonymization.generalization import Generalization
from anonymization.pseudoanonymization import PseudoAnonymization


LGPD_COLUMNS = [
    "cpf",
    "data_nascimento",
    "declara_bens",
    "cargo",
    "etnia",
    "estado_civil",
    "genero",
    "grau_instrucao",
    "nacionalidade",
    "ocupacao",
    "unidade_eleitoral",
    "despesa_maxima_campanha",
    "email",
    "nome",
    "municipio_nascimento",
    "partido",
    "nome_social",
    "nome_urna",
    "sigla_partido",
    "sigla_unidade_federativa",
    "sigla_unidade_federativa_nascimento",
    "titulo_eleitoral",
]

rules = {
    "cpf": {"type": "crop", "start": 0, "stop": 5},
    "despesa_maxima_campanha": {"type": "hist", "nbins": 20},
    "email": {"type": "crop", "start": 0, "stop": 5},
    "nome": {"type": "split", "char": " ", "keep": 0},
    "nome_social": {"type": "split", "char": " ", "keep": 0},
    "nome_urna": {"type": "split", "char": " ", "keep": 0},
    "titulo_eleitoral": {"type": "crop", "start": 0, "stop": 5},
}


from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import (
    cross_validate,
    GridSearchCV,
    RepeatedStratifiedKFold,
)

params = {
    "n_estimators": [10, 20, 50, 100],
    "max_features": [None, "sqrt", "log2"],
    "bootstrap": [True, False],
    "class_weight": [None, "balanced", "balanced_subsample"],
}

# clf = Pipeline([('estimator', GridSearchCV(RandomForestClassifier(), param_grid=params, scoring='accuracy',
#                 cv=RepeatedStratifiedKFold(n_splits=4, n_repeats=3, random_state=42)))]).fit(X, y) # Grid search
# clf['estimator'].best_params_

# df = pd.read_parquet("datasets/eleicoes.parquet")
# valid_rows = cleaner(df)
# v = valid_rows.sum() / len(df.index)
# v_cols = v.loc[v >= 0.85]

# ['ano', 'data_nascimento', 'cargo', 'eleicao', 'estado_civil', 'genero',
#  'grau_instrucao', 'nacionalidade', 'ocupacao',
#  'despesa_maxima_campanha', 'nome', 'partido', 'tipo_eleicao',
#  'nome_urna', 'sigla_partido', 'sigla_unidade_federativa',
#  'sigla_unidade_federativa_nascimento']


def learn(df, y, out_filename):
    X = df[
        [
            "ano",
            "data_nascimento",
            "cargo",
            "eleicao",
            "estado_civil",
            "genero",
            "grau_instrucao",
            "nacionalidade",
            "ocupacao",
            "tipo_eleicao",
            "sigla_partido",
            "sigla_unidade_federativa",
            "sigla_unidade_federativa_nascimento",
        ]
    ].iloc[:30000]

    enc = {}
    for c in X.select_dtypes(include=["string", "object", "category"]).columns:
        enc[c] = LabelEncoder()
        X.loc[X.index, c] = enc[c].fit_transform(X[c].astype(str)).astype(int)
    X.fillna(-1, inplace=True)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42
    )

    rf = RandomForestClassifier(
        bootstrap=True,
        class_weight="balanced_subsample",
        max_features=None,
        n_estimators=100,
    )
    rf.fit(X_train, y_train)
    predictions = rf.predict(X_test)

    plt.figure()
    plot_confusion_matrix(
        rf,
        X_test,
        y_test,
        cmap="viridis",
        normalize="all",
        display_labels=["F", "V"],
    )
    plt.xlabel('Classes previstas')
    plt.ylabel('Classes verdadeiras')
    plt.grid(False)
    plt.tight_layout()
    plt.savefig(f"{out_filename.replace('rf', 'rf_cf').replace('.json', '.png')}")

    metrics = precision_recall_fscore_support(y_test, predictions)
    final = {
        "confusion_matrix": confusion_matrix(y_test, predictions).tolist(),
        "accuracy_score": accuracy_score(y_test, predictions),
        "adjusted_rand_score": adjusted_rand_score(y_test, predictions),
        "precision": metrics[0].tolist(),
        "recall": metrics[1].tolist(),
        "fscore": metrics[2].tolist(),
        "support": metrics[3].tolist(),
    }

    with open(out_filename, "w") as f:
        json.dump(final, f, indent=4, sort_keys=False)


################################
# learn
################################

df = pd.read_parquet("datasets/eleicoes.parquet")
y = df["despesa_maxima_campanha"].iloc[:30000]
y = (y > y.median()).astype(int)

learn(df, y, "output/rf_eleicoes_raw.json")
learn(Supression.anonymize(df, LGPD_COLUMNS), y, "output/rf_eleicoes_supression.json")
learn(
    Randomization.anonymize(df, LGPD_COLUMNS),
    y,
    "output/rf_eleicoes_randomization.json",
)
learn(
    Generalization.anonymize(df, LGPD_COLUMNS, rules),
    y,
    "output/rf_eleicoes_generalization.json",
)
learn(
    PseudoAnonymization.anonymize(df, LGPD_COLUMNS),
    y,
    "output/rf_eleicoes_pseudoanonymization.json",
)
