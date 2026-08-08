"""Rule pack validation.

/admin/rules lets a non-programmer edit the thing the whole product depends
on. Validation here is the guard rail: a pack that would silently produce no
findings, or reference a document type that cannot exist, is rejected at save
time rather than discovered when a customer's report comes back empty.
"""

from __future__ import annotations

from .pipeline.doctypes import DOC_TYPES

RULE_TYPES = {
    "field_consistency",
    "financial_sufficiency",
    "statement_recency",
    "statement_history",
    "sudden_deposit",
    "passport_validity",
    "date_coverage",
    "numeric_min",
    "boolean_required",
    "date_order",
    "document_age",
    "photo_spec",
    "profile_documents",
}
SEVERITIES = {"critical", "warning", "info"}

# Where a requirement comes from. Recorded per rule so a report can tell the
# user whether a finding rests on law or on our own judgement.
AUTHORITIES = {
    "law",            # statute or regulation, e.g. EU Visa Code Art. 15
    "member_state",   # a state's own published figure, e.g. Spain's SMI rule
    "official_guidance",  # published consulate / ministry guidance
    "heuristic",      # our own calibration, not an official requirement
}

REQUIRED_PARAMS: dict[str, list[str]] = {
    "field_consistency": ["field", "across"],
    "financial_sufficiency": ["method"],
    "statement_recency": ["max_age_days"],
    "statement_history": ["min_months"],
    "sudden_deposit": ["ratio"],
    "passport_validity": ["min_days_after_return"],
    "date_coverage": ["document"],
    "numeric_min": ["document", "field", "min"],
    "boolean_required": ["document", "field"],
    "date_order": ["a_document", "a_field", "b_document", "b_field"],
    "document_age": ["document", "max_age_days"],
    "photo_spec": [],
    "profile_documents": ["any_of"],
}


def validate_pack(pack: dict) -> list[str]:
    """Return a list of human-readable problems. Empty means valid."""
    errors: list[str] = []

    if not isinstance(pack, dict):
        return ["Rule pack must be a JSON object."]

    for key in ("version", "title", "currency"):
        if not pack.get(key):
            errors.append(f"Missing required top-level field '{key}'.")

    # --- documents ---
    documents = pack.get("documents")
    if not isinstance(documents, list) or not documents:
        errors.append("'documents' must be a non-empty list — this is the checklist.")
        documents = []

    seen_keys: set[str] = set()
    for i, spec in enumerate(documents):
        where = f"documents[{i}]"
        if not isinstance(spec, dict):
            errors.append(f"{where} must be an object.")
            continue
        key = spec.get("key")
        if not key:
            errors.append(f"{where} is missing 'key'.")
            continue
        if key not in DOC_TYPES:
            errors.append(
                f"{where}: unknown document type '{key}'. Known types: "
                + ", ".join(sorted(DOC_TYPES))
            )
        if key in seen_keys:
            errors.append(f"{where}: duplicate document key '{key}'.")
        seen_keys.add(key)

        sev = spec.get("severity", "critical")
        if sev not in SEVERITIES:
            errors.append(f"{where}: severity must be one of {sorted(SEVERITIES)}.")
        if spec.get("required") and not spec.get("fix"):
            errors.append(
                f"{where}: a required document needs a 'fix' telling the applicant "
                "how to obtain it."
            )
        for alt in spec.get("satisfied_by") or []:
            if alt not in DOC_TYPES:
                errors.append(f"{where}: unknown alternative document type '{alt}'.")

    # --- rules ---
    rules = pack.get("rules")
    if rules is None:
        rules = []
    if not isinstance(rules, list):
        errors.append("'rules' must be a list.")
        rules = []

    seen_ids: set[str] = set()
    for i, rule in enumerate(rules):
        where = f"rules[{i}]"
        if not isinstance(rule, dict):
            errors.append(f"{where} must be an object.")
            continue

        rid = rule.get("id")
        if not rid:
            errors.append(f"{where} is missing 'id'.")
        elif rid in seen_ids:
            errors.append(f"{where}: duplicate rule id '{rid}'.")
        else:
            seen_ids.add(rid)

        rtype = rule.get("type")
        if rtype not in RULE_TYPES:
            errors.append(
                f"{where}: unknown rule type '{rtype}'. Supported: "
                + ", ".join(sorted(RULE_TYPES))
            )
            continue

        if rule.get("severity", "warning") not in SEVERITIES:
            errors.append(f"{where}: severity must be one of {sorted(SEVERITIES)}.")

        authority = rule.get("authority")
        if authority is not None and authority not in AUTHORITIES:
            errors.append(
                f"{where}: authority must be one of {sorted(AUTHORITIES)}."
            )
        srcs = rule.get("sources")
        if srcs is not None and not isinstance(srcs, list):
            errors.append(f"{where}: 'sources' must be a list of URLs.")
        # A rule presented as law must say where that law is written.
        if authority in ("law", "member_state") and not srcs:
            errors.append(
                f"{where}: authority '{authority}' requires at least one entry in "
                "'sources' — a requirement claimed as official must cite it."
            )

        params = rule.get("params") or {}
        if not isinstance(params, dict):
            errors.append(f"{where}: 'params' must be an object.")
            continue
        for required in REQUIRED_PARAMS.get(rtype, []):
            if params.get(required) in (None, "", []):
                errors.append(f"{where}: rule type '{rtype}' requires params.{required}.")

        errors.extend(_validate_doc_refs(where, rtype, params))
        errors.extend(_validate_ranges(where, rtype, params))

    # --- currency / fx ---
    fx = pack.get("fx") or {}
    if fx:
        if not fx.get("base"):
            errors.append("'fx' is present but has no 'base' currency.")
        if not isinstance(fx.get("rates"), dict):
            errors.append("'fx.rates' must be an object mapping currency code to rate.")
        else:
            for code, rate in fx["rates"].items():
                if not isinstance(rate, (int, float)) or rate <= 0:
                    errors.append(f"fx.rates.{code} must be a positive number.")

    weights = pack.get("severity_weights")
    if weights is not None:
        if not isinstance(weights, dict):
            errors.append("'severity_weights' must be an object.")
        else:
            for sev, value in weights.items():
                if sev not in SEVERITIES:
                    errors.append(f"severity_weights: unknown severity '{sev}'.")
                elif not isinstance(value, (int, float)) or value < 0:
                    errors.append(f"severity_weights.{sev} must be a non-negative number.")

    # --- llm review ---
    review = pack.get("llm_review") or {}
    if review:
        criteria = review.get("criteria") or []
        if not isinstance(criteria, list):
            errors.append("'llm_review.criteria' must be a list.")
        else:
            crit_ids: set[str] = set()
            for i, c in enumerate(criteria):
                where = f"llm_review.criteria[{i}]"
                if not isinstance(c, dict):
                    errors.append(f"{where} must be an object.")
                    continue
                if not c.get("id"):
                    errors.append(f"{where} is missing 'id'.")
                elif c["id"] in crit_ids:
                    errors.append(f"{where}: duplicate criterion id '{c['id']}'.")
                else:
                    crit_ids.add(c["id"])
                if not c.get("question"):
                    errors.append(f"{where} is missing 'question'.")
                doc = c.get("document")
                if doc and doc not in DOC_TYPES:
                    errors.append(f"{where}: unknown document type '{doc}'.")
                if c.get("severity", "warning") not in SEVERITIES:
                    errors.append(f"{where}: invalid severity.")

    # --- coherence ---
    if documents and not any(
        d.get("required") for d in documents if isinstance(d, dict)
    ):
        errors.append(
            "No document is marked required — this pack would never report a missing "
            "document."
        )

    return errors


def _validate_doc_refs(where: str, rtype: str, params: dict) -> list[str]:
    errors = []
    single_refs = ("document", "a_document", "b_document")
    for key in single_refs:
        value = params.get(key)
        if value and value not in DOC_TYPES:
            errors.append(f"{where}: params.{key} references unknown type '{value}'.")

    for key in ("across", "source_documents", "any_of"):
        values = params.get(key)
        if values is None:
            continue
        if not isinstance(values, list):
            errors.append(f"{where}: params.{key} must be a list.")
            continue
        for value in values:
            if value not in DOC_TYPES:
                errors.append(
                    f"{where}: params.{key} references unknown type '{value}'."
                )

    aliases = params.get("aliases")
    if aliases is not None:
        if not isinstance(aliases, dict):
            errors.append(f"{where}: params.aliases must be an object.")
        else:
            for dtype in aliases:
                if dtype not in DOC_TYPES:
                    errors.append(
                        f"{where}: params.aliases references unknown type '{dtype}'."
                    )
    return errors


def _validate_ranges(where: str, rtype: str, params: dict) -> list[str]:
    errors = []

    if rtype == "financial_sufficiency":
        method = params.get("method")
        if method not in ("per_day", "fixed", "per_day_plus_fixed"):
            errors.append(
                f"{where}: params.method must be per_day, fixed or per_day_plus_fixed."
            )
        if method in ("per_day", "per_day_plus_fixed") and not params.get("per_day_amount"):
            errors.append(f"{where}: method '{method}' requires params.per_day_amount.")
        if method in ("fixed", "per_day_plus_fixed") and params.get("amount") is None:
            errors.append(f"{where}: method '{method}' requires params.amount.")

    if rtype == "financial_sufficiency":
        table = params.get("per_destination")
        if table is not None:
            if not isinstance(table, dict):
                errors.append(f"{where}: params.per_destination must be an object.")
            else:
                for code, override in table.items():
                    if len(code) != 2 or not code.isalpha():
                        errors.append(
                            f"{where}: per_destination key '{code}' must be an "
                            "ISO-3166 alpha-2 country code."
                        )
                    if not isinstance(override, dict):
                        errors.append(
                            f"{where}: per_destination.{code} must be an object."
                        )

    if rtype == "sudden_deposit":
        ratio = params.get("ratio")
        if isinstance(ratio, (int, float)) and not (0 < ratio <= 1):
            errors.append(f"{where}: params.ratio must be between 0 and 1.")

    if rtype == "date_order":
        if params.get("operator", "lte") not in ("lte", "gte", "eq"):
            errors.append(f"{where}: params.operator must be lte, gte or eq.")

    if rtype == "photo_spec":
        fr = params.get("face_height_ratio")
        if fr is not None:
            if (not isinstance(fr, list) or len(fr) != 2
                    or not all(isinstance(x, (int, float)) for x in fr)
                    or not 0 < fr[0] < fr[1] <= 1):
                errors.append(
                    f"{where}: params.face_height_ratio must be [min, max] with "
                    "0 < min < max <= 1."
                )
        rng = params.get("background_lightness_range")
        if rng is not None:
            if (not isinstance(rng, list) or len(rng) != 2
                    or not all(isinstance(x, (int, float)) for x in rng)
                    or not 0 <= rng[0] < rng[1] <= 1):
                errors.append(
                    f"{where}: params.background_lightness_range must be [min, max] "
                    "within 0..1."
                )

    for key in ("max_age_days", "min_months", "min_days_after_return", "min"):
        value = params.get(key)
        if value is not None and (not isinstance(value, (int, float)) or value < 0):
            errors.append(f"{where}: params.{key} must be a non-negative number.")

    return errors
