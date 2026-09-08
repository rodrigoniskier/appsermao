import unittest
from unittest.mock import patch

from exposibot import ai_service


class AiServiceTestCase(unittest.TestCase):
    def test_compaction_preserves_each_research_lens(self):
        sections = []
        for index in range(1, 9):
            body = (f"argumento-{index} " * 700) + f"\nReferência final {index}: https://example.com/{index}"
            sections.append(f"[LENTE {index}]\n{body}")
        original = "\n\n".join(sections)

        compacted = ai_service.compact_research_notes(original, max_chars=7000)

        self.assertLessEqual(len(compacted), 7000)
        for index in range(1, 9):
            self.assertIn(f"[LENTE {index}]", compacted)
        self.assertIn("https://example.com/8", compacted)
        self.assertIn("nota compactada", compacted)

    def test_sermon_generation_prefers_gemini_when_available(self):
        with (
            patch.object(ai_service.ai_providers, "gemini_client", object()),
            patch.object(ai_service.ai_providers, "groq_client", object()),
            patch.object(ai_service, "_gemini_interaction", return_value='{"ict":"x"}') as gemini,
            patch.object(ai_service, "_groq_sermon_completion") as groq,
        ):
            result, provider = ai_service.generate_sermon_json("prompt", "notas")

        self.assertEqual(result, '{"ict":"x"}')
        self.assertEqual(provider, "gemini")
        gemini.assert_called_once()
        groq.assert_not_called()

        call = gemini.call_args.kwargs
        self.assertIn("português brasileiro", call["system_instruction"].lower())
        self.assertIn("português brasileiro", call["prompt"].lower())

    def test_groq_prompt_requires_ptbr(self):
        self.assertIn("português brasileiro", ai_service.GROQ_COMPACT_HOMILETICS_PROMPT.lower())
        self.assertIn("não preencha ict", ai_service.PTBR_OUTPUT_RULE.lower())

    def test_groq_retries_with_smaller_budget_after_413(self):
        too_large = RuntimeError("413 Request too large: TPM limit 8000")
        with (
            patch.object(ai_service.ai_providers, "gemini_client", None),
            patch.object(ai_service.ai_providers, "groq_client", object()),
            patch.object(
                ai_service,
                "_groq_sermon_completion",
                side_effect=[too_large, '{"ict":"compacto"}'],
            ) as groq,
        ):
            result, provider = ai_service.generate_sermon_json("prompt", "notas longas")

        self.assertEqual(result, '{"ict":"compacto"}')
        self.assertEqual(provider, "groq")
        self.assertEqual(groq.call_count, 2)
        self.assertEqual(groq.call_args_list[0].kwargs["max_chars"], 9000)
        self.assertEqual(groq.call_args_list[1].kwargs["max_chars"], 4500)
        self.assertLess(
            groq.call_args_list[1].kwargs["max_tokens"],
            groq.call_args_list[0].kwargs["max_tokens"],
        )


if __name__ == "__main__":
    unittest.main()
