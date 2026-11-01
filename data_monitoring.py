"""Lightweight data-quality and drift monitoring for pandas DataFrames."""

from __future__ import annotations

from typing import Any

import pandas as pd


class DataMonitor:
	"""Compare incoming batches with a baseline and report actionable alerts."""

	def __init__(
		self,
		baseline: pd.DataFrame,
		*,
		missing_rate_tolerance: float = 0.05,
		numeric_drift_threshold: float = 3.0,
	) -> None:
		if baseline.empty:
			raise ValueError("The baseline DataFrame must not be empty")
		self.baseline = baseline.copy()
		self.missing_rate_tolerance = missing_rate_tolerance
		self.numeric_drift_threshold = numeric_drift_threshold

	def monitor(self, batch: pd.DataFrame) -> dict[str, Any]:
		"""Return schema, missing-value, duplicate, and numeric-drift metrics."""
		baseline_columns = set(self.baseline.columns)
		batch_columns = set(batch.columns)
		missing_columns = sorted(baseline_columns - batch_columns)
		unexpected_columns = sorted(batch_columns - baseline_columns)
		alerts: list[str] = []

		if missing_columns:
			alerts.append(f"Missing columns: {missing_columns}")
		if unexpected_columns:
			alerts.append(f"Unexpected columns: {unexpected_columns}")

		missing_rates: dict[str, dict[str, float]] = {}
		numeric_drift: dict[str, float] = {}
		for column in sorted(baseline_columns & batch_columns):
			baseline_missing = float(self.baseline[column].isna().mean())
			batch_missing = float(batch[column].isna().mean()) if len(batch) else 0.0
			missing_rates[column] = {
				"baseline": baseline_missing,
				"current": batch_missing,
			}
			if batch_missing - baseline_missing > self.missing_rate_tolerance:
				alerts.append(f"Missing-value rate increased for '{column}'")

			if pd.api.types.is_numeric_dtype(self.baseline[column]) and pd.api.types.is_numeric_dtype(batch[column]):
				baseline_values = self.baseline[column].dropna()
				current_values = batch[column].dropna()
				if not baseline_values.empty and not current_values.empty:
					baseline_mean = float(baseline_values.mean())
					current_mean = float(current_values.mean())
					scale = float(baseline_values.std())
					if not pd.notna(scale) or scale == 0:
						scale = max(abs(baseline_mean), 1.0)
					drift = abs(current_mean - baseline_mean) / scale
					numeric_drift[column] = drift
					if drift > self.numeric_drift_threshold:
						alerts.append(f"Numeric drift detected for '{column}' ({drift:.2f} baseline std)")

		duplicate_rate = float(batch.duplicated().mean()) if len(batch) else 0.0
		return {
			"rows": len(batch),
			"columns": len(batch.columns),
			"missing_columns": missing_columns,
			"unexpected_columns": unexpected_columns,
			"missing_rates": missing_rates,
			"numeric_drift": numeric_drift,
			"duplicate_rate": duplicate_rate,
			"alerts": alerts,
			"healthy": not alerts,
		}
