import asyncio
import re
import logging
from groq import Groq

from config import GROQ_API_KEY, GROQ_MODEL, MAX_OUTPUT_TOKENS

client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

executor = None  # inject or import from embedding.py / main app

logger = logging.getLogger("hackrx")

async def generate_answer(question: str, context_chunks: list) -> str:
    if not context_chunks:
        return "Information not found in the policy."

    context = "\n\n".join(context_chunks)
    prompt = f"""Answer the following question from the context provided.

Context:

{context}

Question: {question}

Answer:"""

    def _gen():
        try:
            if client is None:
                logger.error("GROQ_API_KEY is missing. Set it in your .env file.")
                return "Information not found in the policy."

            res = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": "Answer strictly from the provided context. If the answer is not in context, say: Information not found in the policy."
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
                max_tokens=MAX_OUTPUT_TOKENS,
            )
            content = (res.choices[0].message.content or "").strip()
            ans = re.sub(r'\s+', ' ', content)
            return ans if ans else "Information not found in the policy."
        except Exception as e:
            logger.error(f"Error generating answer: {e}")
            return "Information not found in the policy."

    # Use event loop with executor injected or global
    return await asyncio.get_event_loop().run_in_executor(executor, _gen)
