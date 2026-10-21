"""Hard < 2,048 token budgeter and knapsack packing validator across 3 compartments."""

import logging

import tiktoken
from pydantic import BaseModel, ConfigDict

from app.backend.telemetry.events import FailureCode, Severity
from app.backend.telemetry.failure_log import failure_logger
from app.config import settings

logger = logging.getLogger("app.core.token_budget")


class AssembledPrompt(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    system_prompt: str
    rag_context: str
    history_context: str
    system_tokens: int
    rag_tokens: int
    history_tokens: int
    total_tokens: int
    full_prompt_text: str


class TokenBudgeter:
    """Enforces strict <= 2,048 token prompt ceiling across (System 256, RAG 1024, History 768)."""

    def __init__(
        self,
        max_prompt_tokens: int = settings.MAX_PROMPT_TOKENS,
        system_budget: int = settings.SYSTEM_TOKEN_BUDGET,
        rag_budget: int = settings.RAG_TOKEN_BUDGET,
        history_budget: int = settings.HISTORY_TOKEN_BUDGET,
        max_cards_budget: int = settings.MAX_POSITION_CARDS_BUDGET,
    ) -> None:
        self.max_prompt_tokens = max_prompt_tokens
        self.system_budget = system_budget
        self.rag_budget = rag_budget
        self.history_budget = history_budget
        self.max_cards_budget = max_cards_budget
        try:
            self.tokenizer: tiktoken.Encoding | None = tiktoken.get_encoding("cl100k_base")
        except Exception:
            self.tokenizer = None

    def count_tokens(self, text: str) -> int:
        if not text:
            return 0
        if self.tokenizer:
            return len(self.tokenizer.encode(text))
        return max(1, len(text.split()))

    def compute_card_budget_per_agent(self, num_agents: int) -> int:
        """Per-card budget = min(96, floor(384 / N))."""
        if num_agents <= 0:
            return 96
        return min(96, self.max_cards_budget // num_agents)

    def truncate_to_tokens(self, text: str, max_tokens: int) -> tuple[str, int]:
        """Truncate text to fit strictly within max_tokens."""
        if not text:
            return "", 0
        if self.tokenizer:
            tokens = self.tokenizer.encode(text)
            if len(tokens) <= max_tokens:
                return text, len(tokens)
            truncated = self.tokenizer.decode(tokens[:max_tokens])
            return truncated, max_tokens
        else:
            words = text.split()
            target_words = int(max_tokens * 0.75)
            truncated = " ".join(words[:target_words])
            return truncated, len(truncated.split())

    async def assemble_and_pack(
        self,
        system_text: str,
        rag_grounding_text: str,
        position_cards_text: str,
        recent_turns: list[str],
        num_agents: int = 2,
    ) -> AssembledPrompt:
        """Assemble all 3 compartments and validate prompt <= 2,048 tokens."""
        # 1. System Persona (max 256 tokens)
        clean_sys, sys_tok = self.truncate_to_tokens(system_text, self.system_budget)

        # 2. Partitioned RAG Context (max 1,024 tokens)
        clean_rag, rag_tok = self.truncate_to_tokens(rag_grounding_text, self.rag_budget)

        # 3. Shared Debate History (max 768 tokens)
        # Position cards up to 384 tokens
        clean_cards, cards_tok = self.truncate_to_tokens(position_cards_text, self.max_cards_budget)
        remaining_history_budget = max(0, self.history_budget - cards_tok)

        # FIFO recent turns window
        packed_turns: list[str] = []
        turns_tok = 0
        for turn in reversed(recent_turns):
            t_tok = self.count_tokens(turn)
            if turns_tok + t_tok <= remaining_history_budget:
                packed_turns.insert(0, turn)
                turns_tok += t_tok
            else:
                break

        history_text = f"=== CURRENT AGENT POSITIONS ===\n{clean_cards}\n\n=== RECENT TURNS ===\n" + "\n\n".join(packed_turns)
        hist_tok = self.count_tokens(history_text)

        total_tokens = sys_tok + rag_tok + hist_tok

        # Hard invariant assertion: total_tokens <= 2048
        if total_tokens > self.max_prompt_tokens:
            await failure_logger.log_failure(
                code=FailureCode.TOKEN_BUDGET_BREACH,
                message=f"Prompt exceeded 2,048 tokens ({total_tokens} tokens). Truncating history.",
                severity=Severity.ERROR,
                component="token_budget",
            )
            # Emergency trim on history
            allowed_hist = max(0, self.max_prompt_tokens - (sys_tok + rag_tok))
            history_text, hist_tok = self.truncate_to_tokens(history_text, allowed_hist)
            total_tokens = sys_tok + rag_tok + hist_tok

        full_prompt = (
            f"[SYSTEM INSTRUCTIONS]\n{clean_sys}\n\n"
            f"[GROUNDING CONTEXT]\n{clean_rag}\n\n"
            f"[DEBATE MEMORY]\n{history_text}\n\n"
            f"[YOUR ARGUMENT]:"
        )

        return AssembledPrompt(
            system_prompt=clean_sys,
            rag_context=clean_rag,
            history_context=history_text,
            system_tokens=sys_tok,
            rag_tokens=rag_tok,
            history_tokens=hist_tok,
            total_tokens=total_tokens,
            full_prompt_text=full_prompt,
        )


token_budgeter = TokenBudgeter()
