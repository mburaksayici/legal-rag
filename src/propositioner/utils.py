def normalize_title_from_source(source: str) -> str:
	# Placeholder normalizer; can add better heuristics later
	return source.rsplit("/", 1)[-1] if source else ""
