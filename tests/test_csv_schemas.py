"""Unit tests for the CSV column contracts (BACKLOG D4 step 4).

CSVs are user/Excel-editable, so the column header is the contract (no version
field). `validate_csv_columns` turns a missing/renamed header into one clear
up-front KeyError instead of an opaque failure deep in the calculation.
"""

import pandas as pd
import pytest

from districtheatingsim.utilities.csv_schemas import (
    CSV_SCHEMAS,
    required_columns,
    validate_csv_columns,
)


def _building_df():
    return pd.DataFrame(columns=list(required_columns("building")))


def test_complete_building_df_passes():
    validate_csv_columns(_building_df(), "building")  # must not raise


def test_extra_columns_are_allowed():
    df = _building_df()
    df["Adresse"] = []
    df["UTM_X"] = []
    validate_csv_columns(df, "building")  # must not raise


def test_missing_column_raises_and_names_it():
    df = _building_df().drop(columns=["VLT_max"])
    with pytest.raises(KeyError, match="VLT_max"):
        validate_csv_columns(df, "building")


def test_message_lists_all_missing_columns():
    df = _building_df().drop(columns=["VLT_max", "RLT_max"])
    with pytest.raises(KeyError) as exc:
        validate_csv_columns(df, "building")
    msg = str(exc.value)
    assert "VLT_max" in msg and "RLT_max" in msg


def test_coordinates_schema():
    validate_csv_columns(pd.DataFrame(columns=["UTM_X", "UTM_Y"]), "coordinates")
    with pytest.raises(KeyError, match="UTM_Y"):
        validate_csv_columns(pd.DataFrame(columns=["UTM_X"]), "coordinates")


def test_optional_columns_are_not_required():
    # Heizgrenztemperatur etc. are optional → a df without them still validates.
    for opt in CSV_SCHEMAS["building"]["optional"]:
        assert opt not in required_columns("building")
    validate_csv_columns(_building_df(), "building")
