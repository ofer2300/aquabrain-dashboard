"""
ResearchSkill - Autonomous Research using Local LLM
====================================================

Uses Ollama (local LLM on RTX 4060 Ti 16GB VRAM) for:
- Web scraping and content extraction
- Technical summarization
- Code analysis and documentation
- Private/confidential research

Features:
- Zero latency (local inference)
- No data leaves your machine
- Structured JSON output
- Context-aware research

Usage:
    from skills.research_skill import ResearchSkill

    skill = ResearchSkill()
    result = skill.execute({
        "query": "Explain NFPA 13 sprinkler spacing requirements",
        "context": "Fire protection engineering project",
        "output_format": "summary"
    })
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import json
import requests

from skills.base import (
    AquaSkill,
    SkillMetadata,
    SkillCategory,
    InputSchema,
    InputField,
    FieldType,
    ExecutionResult,
    ExecutionStatus,
    register_skill
)

# Import AI Engine for Ollama access
from services.ai_engine import (
    get_ollama_client,
    OLLAMA_BASE_URL,
    LOCAL_MODEL,
    smart_ask
)


# Research-specific system prompts
RESEARCH_SYSTEM_PROMPT = """You are AquaBrain Local - a precision engineering AI running locally on RTX 4060 Ti.

Your capabilities:
1. Technical Documentation Analysis - Extract key information from technical documents
2. Code Analysis - Understand and explain code structure and functionality
3. Engineering Research - Deep knowledge of NFPA, building codes, MEP systems
4. Data Summarization - Condense complex information into actionable insights

Output Guidelines:
- Be concise and precise
- Use bullet points for clarity
- Include relevant citations or references when available
- Highlight key findings and actionable items
- Structure responses in clear sections
- ALWAYS cite NFPA/ISO standards where applicable

For engineering topics, reference relevant standards (NFPA 13, IBC, ת"י 1596, etc.)
For code analysis, explain the logic step by step
For research, provide well-organized summaries with key takeaways

IMPORTANT: You are optimized for engineering precision (Temperature: 0.2). Provide factual, accurate responses."""

CODE_ANALYSIS_PROMPT = """You are an expert code analyst. Analyze the provided code and:
1. Explain what the code does
2. Identify the main functions/classes and their purposes
3. Note any potential issues or improvements
4. Summarize dependencies and requirements
5. Provide a usage example if applicable

Be thorough but concise. Use code blocks for examples."""

SUMMARIZATION_PROMPT = """You are an expert summarizer. Create a structured summary with:
1. **Key Points**: Main takeaways (3-5 bullets)
2. **Details**: Important supporting information
3. **Action Items**: Recommended next steps (if applicable)
4. **References**: Sources or related topics

Keep the summary concise but comprehensive."""


@register_skill
class ResearchSkill(AquaSkill):
    """
    Autonomous research skill using local LLM (Ollama).

    Runs on RTX 4060 Ti with zero latency and full privacy.
    """

    @property
    def metadata(self) -> SkillMetadata:
        return SkillMetadata(
            id="research_local",
            name="Local Research Agent",
            description="Autonomous research and summarization using local LLM (RTX 4060 Ti). Zero latency, full privacy.",
            category=SkillCategory.RESEARCH,
            icon="Search",
            color="#8B5CF6",  # Purple for AI
            version="1.0.0",
            author="AquaBrain",
            tags=["research", "local", "ollama", "ai", "summarization", "analysis"],
            is_async=False,
            estimated_duration_sec=30
        )

    @property
    def input_schema(self) -> InputSchema:
        return InputSchema(fields=[
            InputField(
                name="query",
                label="Research Query",
                type=FieldType.TEXTAREA,
                required=True,
                placeholder="Enter your research question or paste content to analyze...",
                description="The research question, code to analyze, or content to summarize"
            ),
            InputField(
                name="context",
                label="Context (Optional)",
                type=FieldType.TEXTAREA,
                required=False,
                placeholder="Additional context about your project or requirements...",
                description="Background information to improve research relevance"
            ),
            InputField(
                name="research_type",
                label="Research Type",
                type=FieldType.SELECT,
                required=True,
                default="general",
                options=[
                    {"value": "general", "label": "General Research"},
                    {"value": "code_analysis", "label": "Code Analysis"},
                    {"value": "summarization", "label": "Summarization"},
                    {"value": "engineering", "label": "Engineering Research"},
                    {"value": "comparison", "label": "Comparison Analysis"}
                ],
                description="Type of research to perform"
            ),
            InputField(
                name="output_format",
                label="Output Format",
                type=FieldType.SELECT,
                required=True,
                default="structured",
                options=[
                    {"value": "structured", "label": "Structured JSON"},
                    {"value": "markdown", "label": "Markdown Report"},
                    {"value": "bullets", "label": "Bullet Points"},
                    {"value": "detailed", "label": "Detailed Analysis"}
                ],
                description="How to format the research output"
            ),
            InputField(
                name="max_length",
                label="Max Response Length",
                type=FieldType.SELECT,
                required=False,
                default="medium",
                options=[
                    {"value": "short", "label": "Short (500 tokens)"},
                    {"value": "medium", "label": "Medium (1500 tokens)"},
                    {"value": "long", "label": "Long (3000 tokens)"},
                    {"value": "unlimited", "label": "Unlimited"}
                ],
                description="Maximum length of the research output"
            )
        ])

    def execute(self, inputs: Dict[str, Any]) -> ExecutionResult:
        """
        Execute the research query using local Ollama LLM.

        Args:
            inputs: Dictionary containing:
                - query: The research question or content
                - context: Optional background context
                - research_type: Type of research (general, code, summarization, etc.)
                - output_format: How to format output
                - max_length: Response length limit

        Returns:
            ExecutionResult with structured JSON response
        """
        start_time = datetime.now()

        try:
            # Extract inputs
            query = inputs.get("query", "")
            context = inputs.get("context", "")
            research_type = inputs.get("research_type", "general")
            output_format = inputs.get("output_format", "structured")
            max_length = inputs.get("max_length", "medium")

            if not query.strip():
                return ExecutionResult(
                    status=ExecutionStatus.FAILED,
                    skill_id=self.metadata.id,
                    message="Research query cannot be empty",
                    error="Empty query provided"
                )

            # Determine max tokens based on length setting
            max_tokens_map = {
                "short": 500,
                "medium": 1500,
                "long": 3000,
                "unlimited": 4096
            }
            max_tokens = max_tokens_map.get(max_length, 1500)

            # Select system prompt based on research type
            system_prompt = self._get_system_prompt(research_type)

            # Build the full prompt
            full_prompt = self._build_prompt(query, context, research_type, output_format)

            # Check if Ollama is available
            ollama = get_ollama_client()

            if ollama.is_available():
                # Use local LLM (zero latency!)
                provider_used = "ollama"
                response = ollama.generate(
                    prompt=full_prompt,
                    model=LOCAL_MODEL,
                    system_prompt=system_prompt,
                    temperature=0.2,  # Engineering precision - factual responses
                    max_tokens=max_tokens
                )
            else:
                # Fallback to cloud (Gemini)
                provider_used = "gemini (fallback)"
                response = smart_ask(
                    prompt=full_prompt,
                    system_prompt=system_prompt,
                    temperature=0.3,
                    fallback=True
                )

            # Calculate duration
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            # Parse and structure the output
            structured_output = self._structure_output(
                response,
                research_type,
                output_format,
                provider_used
            )

            return ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                skill_id=self.metadata.id,
                message=f"Research completed using {provider_used}",
                output=structured_output,
                duration_ms=duration_ms,
                metrics={
                    "provider": provider_used,
                    "model": LOCAL_MODEL if provider_used == "ollama" else "gemini-2.5-flash",
                    "research_type": research_type,
                    "output_format": output_format,
                    "response_length": len(response),
                    "tokens_estimated": len(response.split()) * 1.3
                }
            )

        except Exception as e:
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            import traceback

            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                skill_id=self.metadata.id,
                message=f"Research failed: {str(e)}",
                error=str(e),
                error_traceback=traceback.format_exc(),
                duration_ms=duration_ms
            )

    def _get_system_prompt(self, research_type: str) -> str:
        """Get the appropriate system prompt for the research type."""
        prompts = {
            "code_analysis": CODE_ANALYSIS_PROMPT,
            "summarization": SUMMARIZATION_PROMPT,
            "general": RESEARCH_SYSTEM_PROMPT,
            "engineering": RESEARCH_SYSTEM_PROMPT + "\n\nFocus on engineering standards, codes, and technical requirements.",
            "comparison": RESEARCH_SYSTEM_PROMPT + "\n\nProvide a structured comparison with pros/cons for each option."
        }
        return prompts.get(research_type, RESEARCH_SYSTEM_PROMPT)

    def _build_prompt(
        self,
        query: str,
        context: str,
        research_type: str,
        output_format: str
    ) -> str:
        """Build the full prompt for the LLM."""

        prompt_parts = []

        # Add context if provided
        if context.strip():
            prompt_parts.append(f"**Context:**\n{context}\n")

        # Add the main query
        prompt_parts.append(f"**Research Request:**\n{query}\n")

        # Add format instructions
        format_instructions = {
            "structured": "Please respond with a structured JSON object containing: { 'summary': string, 'key_points': string[], 'details': string, 'recommendations': string[] }",
            "markdown": "Please respond in well-formatted Markdown with headers, bullet points, and code blocks as needed.",
            "bullets": "Please respond with concise bullet points, organized by topic.",
            "detailed": "Please provide a comprehensive, detailed analysis covering all aspects of the query."
        }

        prompt_parts.append(f"\n**Output Format:**\n{format_instructions.get(output_format, '')}")

        return "\n".join(prompt_parts)

    def _structure_output(
        self,
        response: str,
        research_type: str,
        output_format: str,
        provider: str
    ) -> Dict[str, Any]:
        """Structure the LLM response into a standardized output."""

        output = {
            "raw_response": response,
            "research_type": research_type,
            "output_format": output_format,
            "provider": provider,
            "timestamp": datetime.now().isoformat()
        }

        # Try to parse JSON if structured format was requested
        if output_format == "structured":
            try:
                # Try to extract JSON from response
                import re
                json_match = re.search(r'\{[\s\S]*\}', response)
                if json_match:
                    parsed = json.loads(json_match.group())
                    output["parsed"] = parsed
            except json.JSONDecodeError:
                output["parsed"] = None

        # Extract key sections if markdown
        if output_format == "markdown" or output_format == "detailed":
            sections = self._extract_sections(response)
            output["sections"] = sections

        return output

    def _extract_sections(self, text: str) -> Dict[str, str]:
        """Extract sections from markdown-formatted text."""
        sections = {}
        current_section = "content"
        current_content = []

        for line in text.split("\n"):
            if line.startswith("# ") or line.startswith("## "):
                if current_content:
                    sections[current_section] = "\n".join(current_content).strip()
                current_section = line.lstrip("#").strip().lower().replace(" ", "_")
                current_content = []
            else:
                current_content.append(line)

        if current_content:
            sections[current_section] = "\n".join(current_content).strip()

        return sections


# Quick test function
def test_research_skill():
    """Test the research skill."""
    skill = ResearchSkill()

    print("=" * 60)
    print("🔬 Testing Research Skill (Local LLM)")
    print("=" * 60)

    # Test 1: General research
    print("\n[Test 1] General Research...")
    result = skill.execute({
        "query": "What are the main requirements for sprinkler spacing according to NFPA 13?",
        "context": "Fire protection system design",
        "research_type": "engineering",
        "output_format": "bullets",
        "max_length": "medium"
    })

    print(f"Status: {result.status}")
    print(f"Message: {result.message}")
    print(f"Duration: {result.duration_ms}ms")
    if result.output:
        print(f"Provider: {result.output.get('provider')}")
        print(f"Response preview: {result.output.get('raw_response', '')[:200]}...")

    # Test 2: Code analysis
    print("\n[Test 2] Code Analysis...")
    result = skill.execute({
        "query": """
def calculate_pressure_loss(flow_rate, diameter, length, c_factor=120):
    '''Calculate pressure loss using Hazen-Williams formula'''
    return 4.52 * (flow_rate ** 1.85) / (c_factor ** 1.85 * diameter ** 4.87) * length
        """,
        "research_type": "code_analysis",
        "output_format": "structured",
        "max_length": "medium"
    })

    print(f"Status: {result.status}")
    print(f"Duration: {result.duration_ms}ms")

    print("\n" + "=" * 60)
    print("✅ Research Skill Test Complete")
    print("=" * 60)


if __name__ == "__main__":
    test_research_skill()
