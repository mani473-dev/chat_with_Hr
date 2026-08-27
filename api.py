# ============================================================
# api.py
# ============================================================

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from handler import getOutput


# ============================================================
# FASTAPI APP
# ============================================================

app = FastAPI(
    title="HR Recruitment Q&A API"
)


# ============================================================
# CONVERSATION MEMORY
# ============================================================
#
# POC:
# Store the pending candidate suggestion in memory.
#
# Example:
#
# CONVERSATIONS["default"] = {
#     "original_question":
#         "can u give me the skills of the Mamdou Salem?",
#
#     "requested_candidate":
#         "Mamdou Salem",
#
#     "suggested_candidate":
#         "Mamdouh Salem"
# }
#
# IMPORTANT:
# This memory is cleared when the FastAPI server restarts.
#
# ============================================================

CONVERSATIONS = {}


# ============================================================
# INTERNAL CONVERSATION ID
# ============================================================
#
# User does NOT need to send this in Postman.
#
# For the POC we use one conversation.
#
# ============================================================

CONVERSATION_ID = "default"


# ============================================================
# REQUEST MODEL
# ============================================================

class QuestionRequest(BaseModel):

    question: str


# ============================================================
# ROOT
# ============================================================

@app.get("/")
def home():

    return {
        "message":
            "HR Recruitment Q&A API is running"
    }


# ============================================================
# EXECUTE
# ============================================================

@app.post("/execute")
def execute(
    request: QuestionRequest
):

    try:

        # ====================================================
        # 1. GET USER QUESTION
        # ====================================================

        question = (
            request.question.strip()
        )

        if not question:

            raise HTTPException(
                status_code=400,
                detail="Question cannot be empty."
            )

        # ====================================================
        # 2. GET CONVERSATION MEMORY
        # ====================================================

        conversation_id = (
            CONVERSATION_ID
        )

        previous_state = (
            CONVERSATIONS.get(
                conversation_id
            )
        )

        print(
            "\n========================================"
        )

        print(
            "USER QUESTION"
        )

        print(
            "========================================"
        )

        print(
            question
        )

        print(
            "\nCONVERSATION ID:"
        )

        print(
            conversation_id
        )

        print(
            "\nPREVIOUS CONVERSATION:"
        )

        print(
            previous_state
        )

        # ====================================================
        # 3. CHECK WHETHER THIS IS A FOLLOW-UP
        # ====================================================

        if previous_state:

            # =================================================
            # USER CONFIRMS SUGGESTED CANDIDATE
            # =================================================

            if question.lower() in {

                "yes",
                "y",
                "yeah",
                "yep",
                "correct",
                "yes this candidate",
                "yes that's correct",
                "yes thats correct"
            }:

                print(
                    "\n========================================"
                )

                print(
                    "USER CONFIRMED CANDIDATE"
                )

                print(
                    "========================================"
                )

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

                # =================================================
                # SAFETY CHECK
                # =================================================

                if not (
                    original_question
                    and
                    requested_candidate
                    and
                    suggested_candidate
                ):

                    CONVERSATIONS.pop(
                        conversation_id,
                        None
                    )

                    return {
                        "status":
                            "ERROR",

                        "message":
                            (
                                "The previous candidate "
                                "suggestion could not be recovered."
                            )
                    }

                # =================================================
                # REPLACE WRONG NAME WITH CANONICAL NAME
                # =================================================

                corrected_question = (
                    original_question.replace(
                        requested_candidate,
                        suggested_candidate
                    )
                )

                print(
                    "\nORIGINAL QUESTION:"
                )

                print(
                    original_question
                )

                print(
                    "\nCORRECTED QUESTION:"
                )

                print(
                    corrected_question
                )

                # =================================================
                # CLEAR MEMORY BEFORE RE-RUNNING
                # =================================================

                CONVERSATIONS.pop(
                    conversation_id,
                    None
                )

                # =================================================
                # RUN HR Q&A AGAIN
                # =================================================

                response = getOutput(
                    corrected_question
                )

                return {

                    "question":
                        corrected_question,

                    "status":
                        (
                            response.get(
                                "status",
                                "COMPLETED"
                            )
                            if isinstance(
                                response,
                                dict
                            )
                            else
                            "COMPLETED"
                        ),

                    "message":
                        response
                }

            # =================================================
            # USER REJECTS SUGGESTED CANDIDATE
            # =================================================

            if question.lower() in {

                "no",
                "n",
                "nope",
                "not this one",
                "wrong"
            }:

                print(
                    "\n========================================"
                )

                print(
                    "USER REJECTED CANDIDATE"
                )

                print(
                    "========================================"
                )

                # ------------------------------------------------
                # Do NOT delete the whole conversation.
                # Keep it so the user can provide another name.
                # ------------------------------------------------

                previous_state[
                    "awaiting_candidate"
                ] = True

                CONVERSATIONS[
                    conversation_id
                ] = previous_state

                return {

                    "status":
                        "WAITING_FOR_USER",

                    "message":
                        (
                            "Okay. Tell me the candidate name "
                            "you want to use."
                        ),

                    "state":
                        previous_state
                }

            # =================================================
            # USER PROVIDES A NEW CANDIDATE NAME
            # =================================================
            #
            # Example:
            #
            # no
            #
            # then:
            #
            # Mamdouh Salem
            #
            # =================================================

            if previous_state.get(
                "awaiting_candidate",
                False
            ):

                print(
                    "\n========================================"
                )

                print(
                    "USER PROVIDED NEW CANDIDATE"
                )

                print(
                    "========================================"
                )

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

                if (
                    original_question
                    and
                    requested_candidate
                ):

                    corrected_question = (
                        original_question.replace(
                            requested_candidate,
                            question
                        )
                    )

                    # Clear conversation memory
                    CONVERSATIONS.pop(
                        conversation_id,
                        None
                    )

                    print(
                        "\nUPDATED QUESTION:"
                    )

                    print(
                        corrected_question
                    )

                    response = getOutput(
                        corrected_question
                    )

                    return {

                        "question":
                            corrected_question,

                        "status":
                            (
                                response.get(
                                    "status",
                                    "COMPLETED"
                                )
                                if isinstance(
                                    response,
                                    dict
                                )
                                else
                                "COMPLETED"
                            ),

                        "message":
                            response
                    }

        # ====================================================
        # 4. NEW HR QUESTION
        # ====================================================

        print(
            "\n========================================"
        )

        print(
            "NEW HR QUESTION"
        )

        print(
            "========================================"
        )

        response = getOutput(
            question
        )

        # ====================================================
        # 5. CHECK WHETHER HANDLER FOUND A SUGGESTION
        # ====================================================

        if isinstance(
            response,
            dict
        ):

            response_status = (
                response.get(
                    "status"
                )
            )

            if (
                response_status
                ==
                "WAITING_FOR_USER"
            ):

                requested_candidate = (
                    response.get(
                        "requested_candidate"
                    )
                )

                suggested_candidate = (
                    response.get(
                        "suggested_candidate"
                    )
                )

                original_question = (
                    response.get(
                        "original_question"
                    )
                    or
                    question
                )

                # =================================================
                # SAVE CONVERSATION
                # =================================================

                CONVERSATIONS[
                    conversation_id
                ] = {

                    "original_question":
                        original_question,

                    "requested_candidate":
                        requested_candidate,

                    "suggested_candidate":
                        suggested_candidate,

                    "awaiting_candidate":
                        False
                }

                print(
                    "\n========================================"
                )

                print(
                    "CONVERSATION SAVED"
                )

                print(
                    "========================================"
                )

                print(
                    CONVERSATIONS[
                        conversation_id
                    ]
                )

                return response

        # ====================================================
        # 6. NORMAL RESPONSE
        # ====================================================

        return {

            "status":
                "COMPLETED",

            "message":
                response
        }

    # ========================================================
    # HTTP ERROR
    # ========================================================

    except HTTPException:

        raise

    # ========================================================
    # GENERAL ERROR
    # ========================================================

    except Exception as e:

        print(
            "\n========================================"
        )

        print(
            "ERROR"
        )

        print(
            "========================================"
        )

        print(
            str(e)
        )

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
