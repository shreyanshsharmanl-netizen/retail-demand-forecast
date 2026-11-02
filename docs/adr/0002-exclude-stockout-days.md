# ADR 0002: Exclude stockout days from training

**Status:** accepted

**Context:** On a stockout day, sales equal stock rather than demand. Training on them teaches the model to under-forecast the items that run out most.

**Decision:** Remove those days from training targets and lag features.

**Consequences:** Less biased forecasts, but items that are often out of stock have less history.
