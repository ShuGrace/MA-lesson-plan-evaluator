"""
Multi-Agent Debate Engine - Framework v3.0
Enables agents to review, challenge, and refine each other's evaluations.
"""
import asyncio
import logging
import json
from typing import Dict, List, Optional
from app.services.llm_client import llm_client
from app.config import ENABLE_GPT, ENABLE_CLAUDE, ENABLE_DEEPSEEK

logger = logging.getLogger("lesson-evaluator")


class DebateEngine:
    """Orchestrates multi-round debates between AI agents."""

    def __init__(self):
        self.llm = llm_client
        self.max_rounds = 2

    async def run_debate(
        self,
        initial_evaluations: List[Dict],
        lesson_plan: str,
        lesson_title: str,
    ) -> Dict:
        """
        Run a multi-round debate between agents.

        Round 0: Initial evaluations (already done)
        Round 1: Cross-review (agents see each other's work)
        Round 2: Consensus building (moderator synthesizes)
        """
        logger.info("=" * 50)
        logger.info("DEBATE ENGINE: Starting multi-agent debate")
        logger.info(f"Agents participating: {len(initial_evaluations)}")
        logger.info("=" * 50)

        debate_record = {
            "rounds": [],
            "consensus": None,
            "total_rounds": 0,
        }

        # ── Round 0: Initial evaluations (already done) ──
        debate_record["rounds"].append({
            "round": 0,
            "phase": "independent_evaluation",
            "exchanges": self._format_initial_evaluations(initial_evaluations),
        })

        # ── Round 1: Cross-Review ──
        logger.info("DEBATE Round 1: Cross-Review starting...")
        round1_responses = await self._run_cross_review(
            initial_evaluations, lesson_plan, lesson_title
        )
        debate_record["rounds"].append({
            "round": 1,
            "phase": "cross_review",
            "exchanges": round1_responses,
        })
        logger.info(f"DEBATE Round 1: {len(round1_responses)} reviews completed")

        # ── Round 2: Consensus Building ──
        logger.info("DEBATE Round 2: Consensus building starting...")
        consensus = await self._build_consensus(
            initial_evaluations, round1_responses, lesson_plan, lesson_title
        )
        debate_record["rounds"].append({
            "round": 2,
            "phase": "consensus",
            "exchanges": consensus["responses"],
        })

        debate_record["consensus"] = consensus["final_scores"]
        debate_record["total_rounds"] = 3

        logger.info("DEBATE: Complete")
        logger.info(f"Consensus scores: {consensus['final_scores'].get('consensus_scores', {})}")
        logger.info("=" * 50)

        return debate_record

    def _format_initial_evaluations(self, evaluations: List[Dict]) -> List[Dict]:
        """Format initial evaluations for the debate record."""
        exchanges = []
        for eval_data in evaluations:
            exchanges.append({
                "agent": eval_data.get("agent", "Unknown"),
                "dimension": eval_data.get("dimension", "Unknown"),
                "score": self._extract_score(eval_data),
                "summary": self._extract_summary(eval_data),
            })
        return exchanges

    async def _run_cross_review(
        self,
        initial_evaluations: List[Dict],
        lesson_plan: str,
        lesson_title: str,
    ) -> List[Dict]:
        """Round 1: Each agent reviews other agents' evaluations."""
        all_evals_summary = self._build_evaluation_summary(initial_evaluations)

        tasks = []
        agent_info = []

        for eval_data in initial_evaluations:
            agent_name = eval_data.get("agent", "Unknown")
            dimension = eval_data.get("dimension", "Unknown")
            role = eval_data.get("role", "Specialist")

            prompt = f"""You are {agent_name}, a {role} specialising in {dimension}.

You previously evaluated the lesson plan "{lesson_title}" and gave your assessment.

Here are ALL agents' initial evaluations:
{all_evals_summary}

Now review the other agents' evaluations. Consider:
1. Do you agree or disagree with their scores? Why?
2. Did any agent identify something you missed in your own dimension?
3. Would you adjust your own score after seeing their perspectives?
4. How do the other dimensions interact with yours?

You MUST respond in valid JSON format (no markdown, no extra text):
{{
    "agreements": ["What you agree with from other agents"],
    "disagreements": ["What you disagree with and why"],
    "new_insights": ["Things other agents caught that you missed"],
    "adjusted_score": <your revised score as integer, or same score>,
    "original_score": <your original score as integer>,
    "score_change_reason": "Why you changed or kept your score",
    "cross_dimension_observations": ["How your dimension relates to others"]
}}"""

            agent_info.append({"agent": agent_name, "dimension": dimension})
            tasks.append(self._call_agent_safe(agent_name, prompt))

        # Run all cross-reviews in parallel
        results = await asyncio.gather(*tasks)

        responses = []
        for i, result in enumerate(results):
            info = agent_info[i]
            if result["success"]:
                review = self._parse_json_response(result["response"])
                responses.append({
                    "agent": info["agent"],
                    "dimension": info["dimension"],
                    "review": review,
                })
                logger.info(
                    f"  Cross-review from {info['agent']}: "
                    f"adjusted_score={review.get('adjusted_score', 'N/A')}"
                )
            else:
                responses.append({
                    "agent": info["agent"],
                    "dimension": info["dimension"],
                    "review": {"error": result["error"]},
                })
                logger.error(f"  Cross-review failed for {info['agent']}: {result['error']}")

        return responses

    async def _build_consensus(
        self,
        initial_evaluations: List[Dict],
        cross_reviews: List[Dict],
        lesson_plan: str,
        lesson_title: str,
    ) -> Dict:
        """Round 2: Moderator synthesizes final consensus."""
        debate_summary = self._build_debate_summary(
            initial_evaluations, cross_reviews
        )

        moderator_prompt = f"""You are a Moderator synthesizing a multi-agent debate about the lesson plan "{lesson_title}".

Here is the complete debate record:
{debate_summary}

Based on the agents' initial evaluations, cross-reviews, agreements, and disagreements, determine:

1. Final consensus scores for each dimension (0-100)
2. Key points of agreement across agents
3. Key points of disagreement and how they were resolved
4. Priority recommendations (combining all agents' insights)

The overall score should be a weighted average:
- place_based_learning: 25%
- cultural_responsiveness_integrated: 35%
- critical_pedagogy: 25%
- lesson_design_quality: 15%

You MUST respond in valid JSON format (no markdown, no extra text):
{{
    "consensus_scores": {{
        "place_based_learning": <integer 0-100>,
        "cultural_responsiveness_integrated": <integer 0-100>,
        "critical_pedagogy": <integer 0-100>,
        "lesson_design_quality": <integer 0-100>,
        "overall": <integer 0-100 weighted average>
    }},
    "agreements": ["Points all agents agreed on"],
    "resolved_disagreements": [
        {{
            "topic": "What was disagreed upon",
            "resolution": "How it was resolved",
            "final_position": "The consensus position"
        }}
    ],
    "priority_recommendations": [
        {{
            "priority": "HIGH",
            "recommendation": "What to improve",
            "rationale": "Why, based on multi-agent consensus",
            "supporting_agents": ["Which agents support this"]
        }}
    ],
    "confidence_level": "HIGH or MEDIUM or LOW",
    "confidence_reason": "Why this confidence level"
}}"""

        try:
            result = await self._call_agent_safe("moderator", moderator_prompt)

            if result["success"]:
                final_scores = self._parse_json_response(result["response"])
                logger.info(f"Moderator consensus achieved: {final_scores.get('consensus_scores', {})}")
                return {
                    "responses": [{"agent": "moderator", "synthesis": final_scores}],
                    "final_scores": final_scores,
                }
            else:
                raise Exception(result["error"])

        except Exception as e:
            logger.error(f"Consensus building failed: {e}")
            fallback = self._calculate_fallback_consensus(
                initial_evaluations, cross_reviews
            )
            return {
                "responses": [{"agent": "moderator", "error": str(e)}],
                "final_scores": fallback,
            }

    # ────────────────────────────────────────
    # Helper methods
    # ────────────────────────────────────────

    async def _call_agent_safe(self, agent_name: str, prompt: str) -> Dict:
        """Call LLM with error handling. Returns {success, response/error}."""
        try:
            provider = self._resolve_provider(agent_name)
            response = await asyncio.wait_for(
                self.llm.call(provider, prompt),
                timeout=120,
            )
            return {"success": True, "response": response}
        except asyncio.TimeoutError:
            return {"success": False, "error": f"Timeout for {agent_name}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _resolve_provider(self, agent_name: str) -> str:
        """Map agent name to LLM provider."""
        name_lower = agent_name.lower()
        if "claude" in name_lower or "cultural" in name_lower:
            if ENABLE_CLAUDE:
                return "claude"
        if "deepseek" in name_lower or "place" in name_lower:
            if ENABLE_DEEPSEEK:
                return "deepseek"
        # Default: GPT (for moderator, GPT agents, and fallback)
        return "chatgpt"

    def _build_evaluation_summary(self, evaluations: List[Dict]) -> str:
        """Create a readable summary of all evaluations."""
        lines = []
        for eval_data in evaluations:
            agent = eval_data.get("agent", "Unknown")
            dimension = eval_data.get("dimension", "Unknown")
            score = self._extract_score(eval_data)

            lines.append(f"\n--- {agent} ({dimension}) ---")
            lines.append(f"Score: {score}/100")

            for dim_key, dim_val in (eval_data.get("analysis") or {}).items():
                if isinstance(dim_val, dict):
                    if dim_val.get("strengths"):
                        lines.append(f"Strengths: {', '.join(str(s) for s in dim_val['strengths'][:3])}")
                    if dim_val.get("areas_for_improvement"):
                        lines.append(f"Improvements: {', '.join(str(s) for s in dim_val['areas_for_improvement'][:3])}")
                    if dim_val.get("recommendations"):
                        lines.append(f"Recommendations: {', '.join(str(s) for s in dim_val['recommendations'][:3])}")

        return "\n".join(lines)

    def _build_debate_summary(
        self, initial_evaluations: List[Dict], cross_reviews: List[Dict]
    ) -> str:
        """Create a summary of the entire debate for the moderator."""
        lines = ["=== INITIAL EVALUATIONS ==="]
        lines.append(self._build_evaluation_summary(initial_evaluations))

        lines.append("\n=== CROSS-REVIEW ROUND ===")
        for review in cross_reviews:
            agent = review.get("agent", "Unknown")
            r = review.get("review", {})
            lines.append(f"\n--- {agent} Cross-Review ---")

            if "error" in r:
                lines.append(f"Error: {r['error']}")
                continue

            if "adjusted_score" in r:
                lines.append(f"Original Score: {r.get('original_score', 'N/A')}")
                lines.append(f"Adjusted Score: {r['adjusted_score']}")
                lines.append(f"Reason: {r.get('score_change_reason', 'N/A')}")
            if "agreements" in r:
                lines.append(f"Agreements: {r['agreements']}")
            if "disagreements" in r:
                lines.append(f"Disagreements: {r['disagreements']}")
            if "new_insights" in r:
                lines.append(f"New Insights: {r['new_insights']}")

        return "\n".join(lines)

    def _extract_score(self, eval_data: Dict) -> Optional[int]:
        """Extract the primary score from an evaluation."""
        # Direct score field
        if eval_data.get("score"):
            return eval_data["score"]
        # From analysis
        if eval_data.get("analysis"):
            for dim_val in eval_data["analysis"].values():
                if isinstance(dim_val, dict) and "score" in dim_val:
                    return dim_val["score"]
        return None

    def _extract_summary(self, eval_data: Dict) -> str:
        """Extract a brief summary from an evaluation."""
        if eval_data.get("recommendations"):
            return "; ".join(str(r) for r in eval_data["recommendations"][:2])
        return "No summary available"

    def _parse_json_response(self, response: str) -> Dict:
        """Parse JSON from LLM response, handling markdown code blocks."""
        cleaned = response.strip()

        # Remove markdown code blocks
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            lines = lines[1:]  # Remove opening ```json
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            cleaned = "\n".join(lines)

        # Try to extract JSON from mixed text
        start = cleaned.find("{")
        end = cleaned.rfind("}") + 1
        if start >= 0 and end > start:
            cleaned = cleaned[start:end]

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse error: {e}")
            logger.warning(f"Raw response (first 500): {response[:500]}")
            return {"raw_response": response[:1000], "parse_error": True}

    def _calculate_fallback_consensus(
        self, initial_evaluations: List[Dict], cross_reviews: List[Dict]
    ) -> Dict:
        """Fallback: use adjusted scores from cross-review, or original scores."""
        scores = {}

        # Try adjusted scores from cross-reviews first
        for review in cross_reviews:
            dim = review.get("dimension", "")
            r = review.get("review", {})
            if isinstance(r, dict) and "adjusted_score" in r:
                try:
                    scores[dim] = int(r["adjusted_score"])
                except (ValueError, TypeError):
                    pass

        # Fill in from initial evaluations if missing
        for eval_data in initial_evaluations:
            dim = eval_data.get("dimension", "")
            if dim and dim not in scores:
                score = self._extract_score(eval_data)
                if score:
                    scores[dim] = score

        # Calculate overall
        weights = {
            "place_based_learning": 0.25,
            "cultural_responsiveness_integrated": 0.35,
            "critical_pedagogy": 0.25,
            "lesson_design_quality": 0.15,
        }
        total_weight = sum(weights.get(k, 0) for k in scores)
        if total_weight > 0:
            overall = sum(
                scores[k] * weights.get(k, 0) / total_weight
                for k in scores
            )
            scores["overall"] = round(overall)

        logger.info(f"Fallback consensus scores: {scores}")

        return {
            "consensus_scores": scores,
            "fallback": True,
            "confidence_level": "LOW",
            "confidence_reason": "Moderator failed, using averaged scores",
        }