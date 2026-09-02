# ===============================================
# handler.py
# ============================================================

import json

from main import (
    executeSql,
    get_hr_data,
    extract_candidate_name,
    llm_intent
)

from candidate_resolver import (
    resolve_candidate_from_dataframe
)


# ============================================================
# UNDERSTAND CONVERSATION RESPONSE
# ============================================================

def understand_conversation_response(
    user_message: str,
    previous_state: dict
) -> dict:
    """
    Use the existing OCI LLM from main.py to understand
    the user's response based on the previous conversation.

    Possible intents:

        CONFIRM
        REJECT
        CHANGE
        CONTINUE
        OTHER

    CHANGE may also contain a new candidate name.
    """

    if not user_message:
        return {
            "intent": "OTHER",
            "candidate_name": None
        }

    if not isinstance(
        previous_state,
        dict
    ):
        return {
            "intent": "OTHER",
            "candidate_name": None
        }

    # ========================================================
    # GET PREVIOUS CONTEXT
    # ========================================================

    original_question = (
        previous_state.get(
            "original_question"
        )
    )

    requested_candidate = (
        previous_state.get(
            "requested_candidate"
        )
    )

    suggested_candidate = (
        previous_state.get(
            "suggested_candidate"
        )
    )

    # ========================================================
    # PROMPT
    # ========================================================

    prompt = f"""
You are a conversation understanding assistant
for an HR recruitment application.

Understand the meaning of the user's current message
using the previous conversation context.

DO NOT answer the HR question.

DO NOT invent candidate information.

DO NOT perform database operations.

Previous conversation:

Original question:
{original_question}

Requested candidate:
{requested_candidate}

Suggested candidate:
{suggested_candidate}

Current user message:
{user_message}

Classify the current user message into exactly ONE
of these intents:

CONFIRM
REJECT
CHANGE
CONTINUE
OTHER

Meaning of each intent:

CONFIRM:
The user accepts, agrees with, or confirms the
previously suggested candidate.

Examples:
"Yes"
"That's correct"
"Yes, that's the person"
"Go ahead with that candidate"
"Use that candidate"
"That is the person I meant"

REJECT:
The user rejects the suggested candidate but does
not clearly provide another candidate name.

Examples:
"No"
"That's not the person"
"That candidate is wrong"
"No, find another person"

CHANGE:
The user rejects or replaces the suggested candidate
and provides another candidate name.

Examples:
"No, I meant Charles Wood"
"Actually use John Smith"
"I meant Charles Wood"
"Use Mamdouh Salem instead"

For CHANGE, extract the new candidate name.

CONTINUE:
The user is continuing or asking something related
to the previous conversation.

Examples:
"What are his skills?"
"What is his experience?"
"Tell me about this candidate"
"What about his interview status?"

OTHER:
The message is unclear or does not fit the categories.

IMPORTANT RULES:

- Do not depend on exact keywords.
- Understand the complete meaning of the message.
- Do not restrict the user to specific confirmation words.
- A natural sentence expressing agreement should be CONFIRM.
- A natural sentence rejecting the candidate should be REJECT.
- If another candidate is explicitly mentioned, classify as CHANGE.
- If the user asks another question about the previous topic,
  classify as CONTINUE.

Return ONLY valid JSON.

Required format:

{{
    "intent": "CONFIRM",
    "candidate_name": null
}}

For CHANGE:

{{
    "intent": "CHANGE",
    "candidate_name": "Charles Wood"
}}

Allowed intent values:

CONFIRM
REJECT
CHANGE
CONTINUE
OTHER

candidate_name must be null unless intent is CHANGE.
"""

    # ========================================================
    # CALL EXISTING OCI LLM
    # ========================================================

    response = llm_intent.invoke(
        prompt
    )

    # ========================================================
    # GET TEXT FROM LLM RESPONSE
    # ========================================================

    if hasattr(
        response,
        "content"
    ):

        content = response.content

    else:

        content = str(
            response
        )

    content = (
        content
        .strip()
    )

    print(
        "\n========================================"
    )

    print(
        "RAW CONVERSATION LLM RESPONSE"
    )

    print(
        "========================================"
    )

    print(
        content
    )

    # ========================================================
    # PARSE JSON
    # ========================================================

    try:

        result = json.loads(
            content
        )

    except json.JSONDecodeError:

        # Handle markdown JSON if model returns:
        #
        # ```json
        # {...}
        # ```

        cleaned_content = (
            content
            .replace(
                "```json",
                ""
            )
            .replace(
                "```",
                ""
            )
            .strip()
        )

        try:

            result = json.loads(
                cleaned_content
            )

        except json.JSONDecodeError:

            print(
                "\nConversation LLM returned invalid JSON."
            )

            return {
                "intent": "OTHER",
                "candidate_name": None
            }

    # ========================================================
    # VALIDATE RESULT
    # ========================================================

    if not isinstance(
        result,
        dict
    ):

        return {
            "intent": "OTHER",
            "candidate_name": None
        }

    intent = (
        str(
            result.get(
                "intent",
                "OTHER"
            )
        )
        .strip()
        .upper()
    )

    allowed_intents = {
        "CONFIRM",
        "REJECT",
        "CHANGE",
        "CONTINUE",
        "OTHER"
    }

    if intent not in allowed_intents:

        intent = "OTHER"

    candidate_name = (
        result.get(
            "candidate_name"
        )
    )

    if candidate_name:

        candidate_name = (
            str(
                candidate_name
            )
            .strip()
        )

    else:

        candidate_name = None

    final_result = {

        "intent":
            intent,

        "candidate_name":
            candidate_name
    }

    print(
        "\n========================================"
    )

    print(
        "PARSED CONVERSATION DECISION"
    )

    print(
        "========================================"
    )

    print(
        final_result
    )

    return final_result


# ============================================================
# GET HR OUTPUT
# ============================================================

def getOutput(
    question: str,
    conversation_id: str | None = None
):

    print(
        "GET HR OUTPUT START"
    )

    print(
        "Conversation ID:",
        conversation_id
    )

    # ========================================================
    # 1. GET HR DATA
    # ========================================================

    master_df, work_experience_df = (
        get_hr_data()
    )

    print(
        "Master rows:",
        len(master_df)
    )

    print(
        "Work experience rows:",
        len(work_experience_df)
    )

    # ========================================================
    # 2. EXTRACT CANDIDATE NAME
    # ========================================================

    requested_candidate = (
        extract_candidate_name(
            question
        )
    )

    print(
        "\nREQUESTED CANDIDATE:"
    )

    print(
        requested_candidate
    )

    # ========================================================
    # 3. RESOLVE CANDIDATE NAME
    # ========================================================

    if requested_candidate:

        candidate_match = (
            resolve_candidate_from_dataframe(
                master_df,
                requested_candidate
            )
        )

        print(
            "\nCANDIDATE MATCH RESULT:"
        )

        print(
            candidate_match
        )

        # ====================================================
        # 3A. FUZZY MATCH / SUGGESTION
        # ====================================================

        if (
            candidate_match
            and
            candidate_match.get(
                "status"
            )
            ==
            "SUGGEST"
        ):

            suggested_name = (
                candidate_match.get(
                    "actual_name"
                )
            )

            return {

                "status":
                    "WAITING_FOR_USER",

                "candidate_match":
                    "SUGGEST",

                "requested_candidate":
                    requested_candidate,

                "suggested_candidate":
                    suggested_name,

                "original_question":
                    question,

                "conversationId":
                    conversation_id,

                "message":
                    (
                        f"I couldn't find an exact match "
                        f"for '{requested_candidate}'. "
                        f"Did you mean '{suggested_name}'?"
                    )
            }

        # ====================================================
        # 3B. CANDIDATE NOT FOUND
        # ====================================================

        if (
            candidate_match
            and
            candidate_match.get(
                "status"
            )
            ==
            "NOT_FOUND"
        ):

            return {

                "status":
                    "NOT_FOUND",

                "candidate_match":
                    "NOT_FOUND",

                "requested_candidate":
                    requested_candidate,

                "original_question":
                    question,

                "conversationId":
                    conversation_id,

                "message":
                    (
                        f"I couldn't find a candidate "
                        f"matching '{requested_candidate}'."
                    )
            }

        # ====================================================
        # 3C. EXACT MATCH
        # ====================================================

        if (
            candidate_match
            and
            candidate_match.get(
                "status"
            )
            ==
            "EXACT"
        ):

            canonical_name = (
                candidate_match.get(
                    "actual_name"
                )
            )

            print(
                "\nCANDIDATE EXACT MATCH:"
            )

            print(
                canonical_name
            )

            # ------------------------------------------------
            # Replace the user's spelling with the canonical
            # candidate name before SQL generation.
            # ------------------------------------------------

            if (
                canonical_name
                and
                requested_candidate
                !=
                canonical_name
            ):

                question = (
                    question.replace(
                        requested_candidate,
                        canonical_name
                    )
                )

                print(
                    "\nUPDATED QUESTION:"
                )

                print(
                    question
                )

    # ========================================================
    # 4. NORMAL HR Q&A
    # ========================================================

    response = executeSql(
        question,
        master_df,
        work_experience_df
    )

    print(
        "GET HR OUTPUT END"
    )

    # ========================================================
    # 5. PRESERVE CONVERSATION ID
    # ========================================================

    if isinstance(
        response,
        dict
    ):

        response.setdefault(
            "conversationId",
            conversation_id
        )

    return response

