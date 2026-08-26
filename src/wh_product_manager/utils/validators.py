from typing import Any


def _missing_size_title(variant: Any) -> bool:
	size_title = getattr(variant, "size_title", None)
	return size_title is None or str(size_title).strip() == ""


def validate_variant_size_titles(
	variants: list[Any],
	*,
	product_label: str,
) -> None:
	"""
	Business rule:
	- If product has 1 variant, size_title can be empty.
	- If product has 2+ variants, every variant must have size_title.
	"""
	if len(variants) <= 1:
		return

	missing_skus: list[str] = []

	for variant in variants:
		if _missing_size_title(variant):
			sku = getattr(variant, "sku", None)
			missing_skus.append(str(sku) if sku else "<unknown-sku>")

	if missing_skus:
		raise ValueError(
			"size_title is required for all variants when a product has multiple "
			f"variants. product={product_label}, missing_variant_skus={missing_skus}"
		)
