import json
import os
import logging

from groq import Groq

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny

from .tool_registry import TOOLS, TOOL_REGISTRY


logger = logging.getLogger(__name__)


client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)


class AIChatView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):

        user_message = request.data.get("message")

        if not user_message:
            return Response(
                {"error": "Message is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        messages = [
            {
                "role": "system",
                "content": (
                    "You are Respawn AI, the official AI assistant for "
                    "Respawn Nation, an esports and gaming platform. "

                    "Your primary purpose is to help users with Respawn Nation, "
                    "including tournaments, games, live streams, matches, profiles, "
                    "and other platform features. "

                    "You may also answer general gaming and esports questions. "

                    "For information that belongs to the Respawn Nation platform, "
                    "use the available database tools instead of guessing. "

                    "Never invent tournament, game, stream, match, user, wallet, "
                    "or other platform data. "

                    "Never invent businesses, locations, prices, recommendations, "
                    "or other real-world facts that you do not have a tool or reliable "
                    "source for. "

                    "If the user asks about something unrelated to Respawn Nation "
                    "or gaming, briefly explain that you are focused on Respawn Nation "
                    "and gaming and ask them to ask something related. "

                    "When the user asks for available, open, or registrable tournaments, "
                    "use list_tournaments with status REGISTRATION. "

                    "When the user asks for ongoing, current, or live tournaments, "
                    "use list_tournaments with status LIVE. "

                    "When the user asks for past or completed tournaments, "
                    "use list_tournaments with status COMPLETED. "

                    "When the user asks about a specific tournament, "
                    "use get_tournament. "

                    "For a tournament summary, provide only the information relevant "
                    "to the request. Normally include name, game, status, format, "
                    "registration deadline or tournament date when available, "
                    "prize pool, and winner when a winner exists. "

                    "Do not dump standings, matches, participant lists, internal IDs, "
                    "banner URLs, engine codes, or other internal fields unless "
                    "the user specifically asks for them. "

                    "All monetary amounts provided by Respawn Nation should be presented "
                    "in INR unless the backend explicitly provides another currency. "

                    "Keep responses concise, readable, and useful."
                ),
            },
            {
                "role": "user",
                "content": user_message,
            },
        ]

        try:

            # FIRST LLM CALL
            response = client.chat.completions.create(
                model="openai/gpt-oss-20b",
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
            )

            assistant_message = response.choices[0].message

            # No tool required
            if not assistant_message.tool_calls:

                return Response(
                    {
                        "reply": assistant_message.content
                    },
                    status=status.HTTP_200_OK
                )

            # Add assistant's tool request
            messages.append(assistant_message)

            # Execute requested tools
            for tool_call in assistant_message.tool_calls:

                function_name = tool_call.function.name

                try:
                    function_arguments = json.loads(
                        tool_call.function.arguments
                    )
                except json.JSONDecodeError:

                    return Response(
                        {
                            "error": "Invalid tool arguments returned by AI"
                        },
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )

                # Security: only registered tools can execute
                if function_name not in TOOL_REGISTRY:

                    logger.warning(
                        "AI requested unknown tool: %s",
                        function_name
                    )

                    return Response(
                        {
                            "error": "AI requested an unavailable tool"
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )

                function = TOOL_REGISTRY[function_name]

                # Execute Django tool
                tool_result = function(**function_arguments)

                # Send result back to LLM
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(
                            {
                                "success": tool_result.success,
                                "data": tool_result.data,
                                "error": tool_result.error,
                            },
                            default=str
                        ),
                    }
                )

            # SECOND LLM CALL
            final_response = client.chat.completions.create(
                model="openai/gpt-oss-20b",
                messages=messages,
            )

            return Response(
                {
                    "reply": final_response.choices[0].message.content
                },
                status=status.HTTP_200_OK
            )

        except Exception:

            logger.exception("AI assistant error")

            return Response(
                {
                    "error": "AI service temporarily unavailable"
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )