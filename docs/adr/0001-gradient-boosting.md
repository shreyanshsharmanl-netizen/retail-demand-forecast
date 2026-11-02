# ADR 0001: Use LightGBM over deep forecasting models

**Status:** accepted

**Context:** There are 144 series with mixed categories and promo effects, and training needs to run on a laptop.

**Decision:** Use one global LightGBM model with lag features.

**Consequences:** Fast, simple to explain and strong on tabular data. Trend beyond the training range is handled poorly by trees.
