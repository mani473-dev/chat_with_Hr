
# ============================================================
# api.py
# ============================================================

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from handler import (
    getOutput,
    understand_conversation_response
)


# ============================================================
# FASTAPI APP
# ============================================================

app = FastAPI(
    title="HR Recruitment Q&A API"
)


# ============================================================
# CONVERSATION MEMORY
# ============================================================

# Stores application-level conversation state.
#
# The key is the Oracle conversationId.
#
# Example:
#
# CONVERSATIONS["ABC123"] = {
#     "original_question":
#         "Give me the skills of Mamdou Salem",
#
#     "requested_candidate":
#         "Mamdou Salem",
#
#     "suggested_candidate":
#         "Mamdouh Salem",
#
#     "awaiting_candidate":
#         True
# }

CONVERSATIONS = {}


# ============================================================
# CURRENT ORACLE CONVERSATION ID
# ============================================================

# The External REST Tool does NOT need to send conversationId
# to this FastAPI endpoint.
#
# The first Oracle call starts with None.
#
# Oracle then returns a conversationId.
#
# That same conversationId is reused for subsequent
# requests until the conversation is ended/reset.

ORACLE_CONVERSATION_ID = None


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
        "message": "HR Recruitment Q&A API is running"
    }


# ============================================================
# HELPER:
# EXTRACT ORACLE CONVERSATION ID
# ============================================================

def extract_conversation_id(
    response
):

    if not isinstance(
        response,
        dict
    ):

        return None

    return (
        response.get(
            "conversationId"
        )
        or
        response.get(
            "conversation_id"
        )
    )


# ============================================================
# HELPER:
# SAVE CANDIDATE STATE
# ============================================================

def save_candidate_state(
    conversation_id: str,
    response: dict,
    original_question: str
):

    if not conversation_id:
        return

    CONVERSATIONS[
        conversation_id
    ] = {

        "original_question":
            response.get(
                "original_question"
            )
            or
            original_question,

        "requested_candidate":
            response.get(
                "requested_candidate"
            ),

        "suggested_candidate":
            response.get(
                "suggested_candidate"
            ),

        "awaiting_candidate":
            True
    }


# ============================================================
# HELPER:
# BUILD CORRECTED QUESTION
# ============================================================

def build_corrected_question(
    original_question: str,
    old_candidate: str,
    new_candidate: str
):

    if not (
        original_question
        and
        old_candidate
        and
        new_candidate
    ):

        return original_question

    return original_question.replace(
        old_candidate,
        new_candidate
    )


# ============================================================
# HELPER:
# UPDATE ORACLE CONVERSATION ID
# ============================================================

def update_oracle_conversation_id(
    response
):

    global ORACLE_CONVERSATION_ID

    returned_conversation_id = (
        extract_conversation_id(
            response
        )
    )

    if returned_conversation_id:

        ORACLE_CONVERSATION_ID = (
            returned_conversation_id
        )

    return ORACLE_CONVERSATION_ID


# ============================================================
# EXECUTE
# ============================================================

@app.post("/execute")
def execute(
    request: QuestionRequest
):

    global ORACLE_CONVERSATION_ID

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
        # 2. CURRENT ORACLE CONVERSATION
        # ====================================================

        conversation_id = (
            ORACLE_CONVERSATION_ID
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
            "\nORACLE CONVERSATION ID:"
        )

        print(
            conversation_id
        )


        # ====================================================
        # 3. GET APPLICATION MEMORY
        # ====================================================

        previous_state = None

        if conversation_id:

            previous_state = (
                CONVERSATIONS.get(
                    conversation_id
                )
            )


        print(
            "\nPREVIOUS APPLICATION STATE:"
        )

        print(
            previous_state
        )


        # ====================================================
        # 4. EXISTING CONVERSATION
        # ====================================================

        if (
            conversation_id
            and
            previous_state
        ):

            print(
                "\n========================================"
            )

            print(
                "EXISTING CONVERSATION"
            )

            print(
                "========================================"
            )


            # =================================================
            # LET LLM UNDERSTAND USER RESPONSE
            # =================================================

            decision = (
                understand_conversation_response(
                    user_message=question,
                    previous_state=previous_state
                )
            )


            print(
                "\nLLM DECISION:"
            )

            print(
                decision
            )


            if not isinstance(
                decision,
                dict
            ):

                raise HTTPException(
                    status_code=500,
                    detail=(
                        "Conversation understanding "
                        "returned an invalid response."
                    )
                )


            intent = (
                str(
                    decision.get(
                        "intent",
                        "OTHER"
                    )
                )
                .strip()
                .upper()
            )


            # =================================================
            # 4A. CONFIRM
            # =================================================

            if intent == "CONFIRM":

                print(
                    "\n========================================"
                )

                print(
                    "LLM DECISION: CONFIRM"
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
                            ),

                        "conversationId":
                            conversation_id
                    }


                corrected_question = (
                    build_corrected_question(
                        original_question,
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


                # ---------------------------------------------
                # REMOVE ONLY PENDING CANDIDATE STATE
                # ---------------------------------------------

                CONVERSATIONS.pop(
                    conversation_id,
                    None
                )


                # ---------------------------------------------
                # CONTINUE SAME ORACLE CONVERSATION
                # ---------------------------------------------

                response = getOutput(
                    corrected_question,
                    conversation_id
                )


                # ---------------------------------------------
                # KEEP ORACLE CONVERSATION ID
                # ---------------------------------------------

                conversation_id = (
                    update_oracle_conversation_id(
                        response
                    )
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
                        response,

                    "conversationId":
                        conversation_id
                }


            # =================================================
            # 4B. REJECT
            # =================================================

            elif intent == "REJECT":

                print(
                    "\n========================================"
                )

                print(
                    "LLM DECISION: REJECT"
                )

                print(
                    "========================================"
                )


                # Keep the state so the user can provide
                # another candidate.

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
                            "Okay. Please provide the "
                            "candidate name you want to use."
                        ),

                    "conversationId":
                        conversation_id
                }


            # =================================================
            # 4C. CHANGE
            # =================================================

            elif intent == "CHANGE":

                print(
                    "\n========================================"
                )

                print(
                    "LLM DECISION: CHANGE"
                )

                print(
                    "========================================"
                )


                new_candidate = (
                    decision.get(
                        "candidate_name"
                    )
                )


                if not new_candidate:

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
                                "Please provide the candidate "
                                "name you want to use."
                            ),

                        "conversationId":
                            conversation_id
                    }


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


                corrected_question = (
                    build_corrected_question(
                        original_question,
                        requested_candidate,
                        new_candidate
                    )
                )


                print(
                    "\nNEW CANDIDATE:"
                )

                print(
                    new_candidate
                )

                print(
                    "\nUPDATED QUESTION:"
                )

                print(
                    corrected_question
                )


                # ---------------------------------------------
                # REMOVE OLD PENDING STATE
                # ---------------------------------------------

                CONVERSATIONS.pop(
                    conversation_id,
                    None
                )


                # ---------------------------------------------
                # CONTINUE SAME ORACLE CONVERSATION
                # ---------------------------------------------

                response = getOutput(
                    corrected_question,
                    conversation_id
                )


                conversation_id = (
                    update_oracle_conversation_id(
                        response
                    )
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
                        response,

                    "conversationId":
                        conversation_id
                }


            # =================================================
            # 4D. CONTINUE
            # =================================================

            elif intent == "CONTINUE":

                print(
                    "\n========================================"
                )

                print(
                    "LLM DECISION: CONTINUE"
                )

                print(
                    "========================================"
                )


                # Send the current question using the
                # SAME Oracle conversationId.

                response = getOutput(
                    question,
                    conversation_id
                )


                conversation_id = (
                    update_oracle_conversation_id(
                        response
                    )
                )


                # ---------------------------------------------
                # Check for another candidate suggestion
                # ---------------------------------------------

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

                        save_candidate_state(
                            conversation_id,
                            response,
                            question
                        )


                return {

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
                        response,

                    "conversationId":
                        conversation_id
                }


            # =================================================
            # 4E. OTHER
            # =================================================

            else:

                print(
                    "\n========================================"
                )

                print(
                    "LLM DECISION: OTHER"
                )

                print(
                    "========================================"
                )


                # Keep using the same Oracle conversation.

                response = getOutput(
                    question,
                    conversation_id
                )


                conversation_id = (
                    update_oracle_conversation_id(
                        response
                    )
                )


                return {

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
                        response,

                    "conversationId":
                        conversation_id
                }


        # ====================================================
        # 5. FIRST REQUEST
        # ====================================================

        print(
            "\n========================================"
        )

        print(
            "FIRST REQUEST / NEW CONVERSATION"
        )

        print(
            "========================================"
        )


        # Since this is the first request,
        # conversation_id is None.
        #
        # getOutput() receives None.
        #
        # The Oracle invocation layer should send:
        #
        # "conversationId": null

        response = getOutput(
            question,
            None
        )


        # ====================================================
        # 6. ORACLE RETURNS CONVERSATION ID
        # ====================================================

        conversation_id = (
            update_oracle_conversation_id(
                response
            )
        )


        print(
            "\nNEW ORACLE CONVERSATION ID:"
        )

        print(
            conversation_id
        )


        # ====================================================
        # 7. CHECK FOR CANDIDATE SUGGESTION
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

                # ---------------------------------------------
                # Oracle must return conversationId so that
                # application state can be stored.
                # ---------------------------------------------

                if not conversation_id:

                    return {

                        "status":
                            "ERROR",

                        "message":
                            (
                                "Oracle did not return a "
                                "conversationId, so the "
                                "conversation state cannot "
                                "be stored safely."
                            )
                    }


                save_candidate_state(
                    conversation_id,
                    response,
                    question
                )


                print(
                    "\n========================================"
                )

                print(
                    "CONVERSATION STATE SAVED"
                )

                print(
                    "========================================"
                )

                print(
                    CONVERSATIONS[
                        conversation_id
                    ]
                )


        # ====================================================
        # 8. NORMAL RESPONSE
        # ====================================================

        return {

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
                response,

            "conversationId":
                conversation_id
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
