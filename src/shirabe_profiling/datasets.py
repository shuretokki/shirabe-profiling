# SPDX-FileCopyrightText: Copyright © 2026 shuretokki
# SPDX-License-Identifier: Apache-2.0

"""Sample tables for the documentation, the tests, and quick experiments."""

from __future__ import annotations

import numpy as np
import polars as pl

__all__ = ["make_homes"]

_DISTRICTS = ("Menteng", "Kemang", "Tebet", "Cibubur", "Bekasi", "Depok")
_DISTRICT_SHARE = (0.10, 0.14, 0.18, 0.22, 0.20, 0.16)
_DISTRICT_EFFECT = {
    "Menteng": 0.90,
    "Kemang": 0.60,
    "Tebet": 0.20,
    "Cibubur": -0.10,
    "Bekasi": -0.30,
    "Depok": -0.25,
}
_COMMISSION_RATE = 0.025


def make_homes(
    n: int = 2000,
    *,
    seed: int = 7,
    nulls: float = 0.09,
) -> pl.DataFrame:
    """Return a synthetic table of homes for sale.

    The table has no real people or addresses, and the same seed always gives the same table.
    The price grows with the area, the district, the garage, and the pool.
    The price falls with the age of the home.
    The price is skewed, so it shows the log transform hint of the Target section.
    The column `agent_commission` is 2.5% of the price.
    A commission is known only after the sale, so it leaks the target on purpose.

    Args:
        n: The number of rows. It must be 1 or more.
        seed: The seed of the random generator. It must be 0 or more.
        nulls: The share of rows with a missing `lot_m2`. It must be between 0 and 1.

    Returns:
        A Polars table with the columns `listing_id`, `district`, `area_m2`, `bedrooms`,
        `garage_spaces`, `has_pool`, `lot_m2`, `year_built`, `listed_on`, `price`,
        and `agent_commission`.

    Raises:
        ValueError: If `n`, `seed`, or `nulls` is outside its range.

    Example:
        >>> from shirabe_profiling.datasets import make_homes
        >>> make_homes(n=3, seed=1).shape
        (3, 11)
    """
    if not isinstance(n, int) or isinstance(n, bool) or n < 1:
        msg = f"n must be an integer >= 1, got {n!r}"
        raise ValueError(msg)
    if not isinstance(seed, int) or isinstance(seed, bool) or seed < 0:
        msg = f"seed must be an integer >= 0, got {seed!r}"
        raise ValueError(msg)
    if not 0.0 <= nulls <= 1.0:
        msg = f"nulls must be between 0 and 1, got {nulls!r}"
        raise ValueError(msg)

    rng = np.random.default_rng(seed)
    district = rng.choice(
        _DISTRICTS,
        n,
        p=_DISTRICT_SHARE,
    )
    area = np.clip(
        rng.lognormal(
            4.5,
            0.45,
            n,
        ),
        24,
        600,
    ).round()
    bedrooms = np.clip(
        np.round(
            area / 45
            + rng.normal(
                0,
                0.7,
                n,
            ),
        ),
        1,
        7,
    )
    garage = np.where(
        rng.random(n) < 0.35,
        0,
        rng.integers(
            1,
            4,
            n,
        ),
    )
    has_pool = rng.random(n) < 0.04
    year_built = rng.integers(
        1975,
        2025,
        n,
    )
    listed_on = np.datetime64("2023-01-01") + rng.integers(
        0,
        1000,
        n,
    ).astype("timedelta64[D]")

    log_price = (
        9.2
        + 0.85 * np.log(area)
        + np.array([_DISTRICT_EFFECT[name] for name in district])
        + 0.07 * garage
        + 0.15 * has_pool
        - 0.004 * (2025 - year_built)
        + rng.normal(
            0,
            0.25,
            n,
        )
    )
    price = np.exp(log_price).round(-3)

    lot = (
        area
        * rng.uniform(
            1.2,
            3.0,
            n,
        )
    ).round()
    lot[rng.random(n) < nulls] = np.nan

    return pl.DataFrame(
        {
            "listing_id": np.arange(
                5000,
                5000 + n,
            ),
            "district": district,
            "area_m2": area.astype(int),
            "bedrooms": bedrooms.astype(int),
            "garage_spaces": garage,
            "has_pool": has_pool,
            "lot_m2": pl.Series(lot).fill_nan(None),
            "year_built": year_built,
            "listed_on": listed_on,
            "price": price.astype(int),
            "agent_commission": (price * _COMMISSION_RATE).round(-3).astype(int),
        },
    )
