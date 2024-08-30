"""Generating deployment files."""

import os, requests

import shutil

from pathlib import Path

import pandas as pd

from sklearn.preprocessing import LabelEncoder

from concrete.ml.sklearn import LogisticRegression as ConcreteLogisticRegression
from concrete.ml.deployment import FHEModelDev

# DownloadData
def download_data():
    os.makedirs('./data', exist_ok=True);

    url_domain = 'https://raw.githubusercontent.com'
    url_folders_path = \
        'anujdutt9/Disease-Prediction-from-Symptoms/master/dataset'
    url_one = f"{url_domain}/{url_folders_path}/training_data.csv"
    url_two = f"{url_domain}/{url_folders_path}/test_data.csv"

    result_one = requests.get(url_one)
    assert result_one.ok == True
    with open(f'./data/Training.csv', 'wb') as f: f.write(result_one.content)

    result_two = requests.get(url_two)
    assert result_two.ok == True
    with open(f'./data/Testing.csv', 'wb') as f: f.write(result_two.content)

    return (len(result_one.content), len(result_two.content))

# DataPreProcessing
def prepare_data():
    """For simplicity sake, we performed a preliminary pre-processing on the data,"""
    """such as correcting column names & encoding the target column then we save in:"""
    """Training_preprocessed.csv ( training set ) & Testing_preprocessed.csv ( test set )."""

    # Files location
    TRAINING_FILE_NAME = "./data/Training.csv"
    TESTING_FILE_NAME = "./data/Testing.csv"

    # Columns processing
    TARGET_COLUMN = "prognosis"
    DROP_COLUMNS = ["Unnamed: 133", "belly_pain", "fluid_overload", "depression", "coma"]

    RENAME_COLUMNS = {
        "scurring": "scurving",                                                                     "dischromic _patches": "dischromic_patches",
        "spotting_ urination": "spotting_urination",                                                "foul_smell_of urine": "foul_smell_of_urine",
        "toxic_look_(typhos)": "toxic_look_(typhus)",                                               "fluid_overload.1": "severe_fluid_overload",
        "extra_marital_contacts": "frequent_unprotected_sexual_intercourse_with_multiple_partners", "history_of_alcohol_consumption": "chronic_alcohol_abuse",
        "diarrhoea": "diarrhea",                                                                    "obesity": "excess_body_fat",
    }

    RENAME_VALUES = {
        "(vertigo) Paroymsal  Positional Vertigo": "Paroxymsal Positional Vertigo",
        "Dimorphic hemmorhoids(piles)": "Dimorphic hemmorhoids (piles)",
        "Peptic ulcer diseae": "Peptic Ulcer",
    }

    """Data preprocessing ( aka prepare_data )"""
    # Load data
    df_train = pd.read_csv(TRAINING_FILE_NAME)
    df_test = pd.read_csv(TESTING_FILE_NAME)

    # Correct some typos in some columns name more exactly 10 typos
    df_train.rename(columns=RENAME_COLUMNS, inplace=True)
    df_test.rename(columns=RENAME_COLUMNS, inplace=True)

    # Correct some typos inside the body of the two CSVs
    df_train[TARGET_COLUMN].replace(RENAME_VALUES.keys(), RENAME_VALUES.values(), inplace=True)
    df_train[TARGET_COLUMN] = df_train[TARGET_COLUMN].apply(str.title)
    df_test[TARGET_COLUMN].replace(RENAME_VALUES.keys(), RENAME_VALUES.values(), inplace=True)
    df_test[TARGET_COLUMN] = df_test[TARGET_COLUMN].apply(str.title)

    # Confusing columns like: ['belly_pain', 'stomach_pain', "abdominal_pain"]
    df_train["stomach_pain"] = (df_train["stomach_pain"] == 1) | (df_train["belly_pain"] == 1)
    df_train["stomach_pain"] = df_train["stomach_pain"].astype(int)
    df_test["stomach_pain"] = (df_test["stomach_pain"] == 1) | (df_test["belly_pain"] == 1)
    df_test["stomach_pain"] = df_test["stomach_pain"].astype(int)

    df_train["severe_fluid_overload"] = (df_train["fluid_overload"] == 1) | (df_train["severe_fluid_overload"] == 1)
    df_train["severe_fluid_overload"] = df_train["severe_fluid_overload"].astype(int)
    df_test["severe_fluid_overload"] = (df_test["fluid_overload"] == 1) | (df_test["severe_fluid_overload"] == 1)
    df_test["severe_fluid_overload"] = df_test["severe_fluid_overload"].astype(int)

    df_train["anxiety"] = (df_train["depression"] == 1) | (df_train["anxiety"] == 1)
    df_train["anxiety"] = df_train["anxiety"].astype(int)
    df_test["anxiety"] = (df_test["depression"] == 1) | (df_test["anxiety"] == 1)
    df_test["anxiety"] = df_test["anxiety"].astype(int)

    # Remove useless columns
    df_train.drop(columns=DROP_COLUMNS, axis=1, errors="ignore", inplace=True)
    df_test.drop(columns=DROP_COLUMNS, axis=1, errors="ignore", inplace=True)

    # Convert the `TARGET_COLUMN` to a numeric label
    label_encoder = LabelEncoder()
    label_encoder.fit(df_train[[TARGET_COLUMN]].values.flatten())

    df_train[f"{TARGET_COLUMN}_encoded"] = label_encoder.transform(df_train[[TARGET_COLUMN]].values.flatten())
    df_test[f"{TARGET_COLUMN}_encoded"] = label_encoder.transform(df_test[[TARGET_COLUMN]].values.flatten())

    # Cast X features from int64 to float32
    float_columns = df_train.columns.drop([TARGET_COLUMN, f"{TARGET_COLUMN}_encoded"])
    df_train[float_columns] = df_train[float_columns].astype("float32")
    df_test[float_columns] = df_test[float_columns].astype("float32")

    # Save preprocessed data
    df_train.to_csv(path_or_buf="./data/Training_preprocessed.csv", index=False)
    df_test.to_csv(path_or_buf="./data/Testing_preprocessed.csv", index=False)

    return df_train, df_test

download_data()

df_train, df_test = prepare_data()

# Split the data into X_train, y_train, X_test_, y_test sets
TARGET_COLUMN = ["prognosis_encoded", "prognosis"]

y_train = df_train[TARGET_COLUMN[0]].values.flatten()
y_test = df_test[TARGET_COLUMN[0]].values.flatten()

X_train = df_train.drop(TARGET_COLUMN, axis=1)
X_test = df_test.drop(TARGET_COLUMN, axis=1)

# Concrete ML model

# Models parameters ( VALS FOUND WITH GRID SEARCH )
optimal_param = {"C": 0.9, "n_bits": 13, "solver": "sag", "multi_class": "auto"}

clf = ConcreteLogisticRegression(**optimal_param)

# Fit the model
clf.fit(X_train, y_train)

# Compile the model
fhe_circuit = clf.compile(X_train)

fhe_circuit.client.keygen(force=False)

path_to_model = Path("./deployment_files/").resolve()

if path_to_model.exists():
    shutil.rmtree(path_to_model)

dev = FHEModelDev(path_to_model, clf)

dev.save(via_mlir=True)
