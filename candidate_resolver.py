# ============================================================
# candidate_resolver.py
# ============================================================

import re

from difflib import SequenceMatcher


# ============================================================
# NORMALIZE NAME
# ============================================================

def normalize_name(
    name: str
) -> str:

    if not name:
        return ""

    name = str(name).strip().lower()

    name = re.sub(
        r"\s+",
        " ",
        name
    )

    return name


# ============================================================
# NAME SIMILARITY
# ============================================================

def name_similarity(
    name1: str,
    name2: str
) -> float:

    return SequenceMatcher(
        None,
        normalize_name(name1),
        normalize_name(name2)
    ).ratio()


# ============================================================
# RESOLVE CANDIDATE NAME
# ============================================================

def resolve_candidate_from_dataframe(
    master_df,
    requested_name: str
):

    if master_df is None:
        return None

    if master_df.empty:
        return None

    if "candidate_name" not in master_df.columns:
        return None

    requested_name = (
        str(requested_name)
        .strip()
    )

    requested_normalized = (
        normalize_name(
            requested_name
        )
    )

    candidate_names = (
        master_df[
            "candidate_name"
        ]
        .dropna()
        .astype(str)
        .str.strip()
        .unique()
        .tolist()
    )

    # ========================================================
    # EXACT CASE-INSENSITIVE MATCH
    # ========================================================

    for candidate_name in candidate_names:

        if (
            normalize_name(candidate_name)
            ==
            requested_normalized
        ):

            return {

                "status":
                    "EXACT",

                "requested_name":
                    requested_name,

                "actual_name":
                    candidate_name,

                "score":
                    1.0
            }

    # ========================================================
    # FUZZY MATCH
    # ========================================================

    best_name = None

    best_score = 0.0

    for candidate_name in candidate_names:

        score = name_similarity(
            requested_name,
            candidate_name
        )

        if score > best_score:

            best_score = score

            best_name = candidate_name

    # ========================================================
    # SUGGEST
    # ========================================================

    if (
        best_name
        and
        best_score >= 0.75
    ):

        return {

            "status":
                "SUGGEST",

            "requested_name":
                requested_name,

            "actual_name":
                best_name,

            "score":
                best_score
        }

    # ========================================================
    # NOT FOUND
    # ========================================================

    return {

        "status":
            "NOT_FOUND",

        "requested_name":
            requested_name,

        "actual_name":
            None,

        "score":
            best_score
    }