# SPDX-FileCopyrightText: Copyright © 2026 shuretokki
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import polars as pl
import pytest

from shirabe_profiling import AlertType, ProfileReport
from shirabe_profiling.datasets import make_homes


class TestMakeHomesShape:
    def test_default_shape(self):
        df = make_homes()
        assert df.shape == (2000, 11)

    def test_columns_and_types(self):
        df = make_homes(n=50)
        assert df.schema == {
            "listing_id": pl.Int64,
            "district": pl.String,
            "area_m2": pl.Int64,
            "bedrooms": pl.Int64,
            "garage_spaces": pl.Int64,
            "has_pool": pl.Boolean,
            "lot_m2": pl.Float64,
            "year_built": pl.Int64,
            "listed_on": pl.Date,
            "price": pl.Int64,
            "agent_commission": pl.Int64,
        }

    def test_listing_ids_are_unique(self):
        assert make_homes(n=300)["listing_id"].n_unique() == 300

    def test_one_row(self):
        assert make_homes(n=1).height == 1


class TestMakeHomesSeed:
    def test_same_seed_gives_same_table(self):
        assert make_homes(
            n=200,
            seed=3,
        ).equals(
            make_homes(
                n=200,
                seed=3,
            ),
        )

    def test_other_seed_gives_other_table(self):
        assert not make_homes(
            n=200,
            seed=3,
        ).equals(
            make_homes(
                n=200,
                seed=4,
            ),
        )


class TestMakeHomesValues:
    def test_missing_share_follows_nulls(self):
        df = make_homes(
            n=4000,
            nulls=0.2,
        )
        share = df["lot_m2"].null_count() / df.height
        assert share == pytest.approx(
            0.2,
            abs=0.03,
        )

    def test_no_nulls(self):
        assert (
            make_homes(
                n=200,
                nulls=0.0,
            )["lot_m2"].null_count()
            == 0
        )

    def test_all_nulls(self):
        assert (
            make_homes(
                n=200,
                nulls=1.0,
            )["lot_m2"].null_count()
            == 200
        )

    def test_price_is_skewed(self):
        assert make_homes()["price"].skew() > 1.0

    def test_commission_is_a_share_of_the_price(self):
        df = make_homes(n=500)
        gap = (df["agent_commission"] - df["price"] * 0.025).abs().max()
        assert gap <= 500

    def test_bedrooms_and_area_are_in_range(self):
        df = make_homes()
        assert df["bedrooms"].min() >= 1
        assert df["bedrooms"].max() <= 7
        assert df["area_m2"].min() >= 24


class TestMakeHomesValidation:
    @pytest.mark.parametrize(
        "n",
        [0, -5, 2.5, "10", None, True],
    )
    def test_bad_n(self, n):
        with pytest.raises(
            ValueError,
            match="n must be an integer >= 1",
        ):
            make_homes(n=n)

    @pytest.mark.parametrize(
        "seed",
        [-1, 1.5, "7", None, False],
    )
    def test_bad_seed(self, seed):
        with pytest.raises(
            ValueError,
            match="seed must be an integer >= 0",
        ):
            make_homes(seed=seed)

    @pytest.mark.parametrize(
        "nulls",
        [-0.1, 1.1],
    )
    def test_bad_nulls(self, nulls):
        with pytest.raises(
            ValueError,
            match="nulls must be between 0 and 1",
        ):
            make_homes(nulls=nulls)


class TestMakeHomesReport:
    def test_report_raises_the_documented_alerts(self):
        report = ProfileReport(
            make_homes(),
            target="price",
        )
        found = {(alert.column, alert.alert_type) for alert in report.alerts}
        assert ("listing_id", AlertType.HIGH_CARDINALITY) in found
        assert ("garage_spaces", AlertType.HIGH_ZEROS) in found
        assert ("lot_m2", AlertType.HIGH_MISSING) in found
        assert ("price", AlertType.SKEWED) in found
        assert ("agent_commission", AlertType.TARGET_LEAKAGE) in found
