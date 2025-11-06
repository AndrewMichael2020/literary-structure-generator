"""
Demo: Phase 5 Evaluation Suite

Demonstrates using the evaluation suite to score a generated draft.

Usage:
    # Offline mode (default, uses MockClient):
    python examples/demo_evaluation.py
    
    # With real LLM stylefit (requires OPENAI_API_KEY):
    OPENAI_API_KEY=xxx python examples/demo_evaluation.py --use-llm
"""

import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from literary_structure_generator.evaluators.evaluate import evaluate_draft, save_eval_report
from literary_structure_generator.models.exemplar_digest import (
    ExemplarDigest,
    MetaInfo as DigestMeta,
)
from literary_structure_generator.models.generation_config import GenerationConfig
from literary_structure_generator.models.story_spec import (
    BeatSpec,
    Character,
    Content,
    Form,
    MetaInfo,
    Setting,
    StorySpec,
)


def main():
    """Run evaluation demo."""
    # Check for --use-llm flag
    use_llm = "--use-llm" in sys.argv
    
    print("=" * 80)
    print("Phase 5 Evaluation Suite Demo")
    print("=" * 80)
    print()
    
    if use_llm:
        print("🔴 Using real LLM for stylefit evaluation")
        print("   (requires OPENAI_API_KEY environment variable)")
    else:
        print("🟢 Using offline MockClient for all evaluations")
    print()
    
    # Create a realistic story spec
    spec = StorySpec(
        meta=MetaInfo(
            story_id="demo_eval_001",
            seed=137,
            version="2.0",
            derived_from={"exemplar": "Emergency", "digest_version": 2},
        ),
        content=Content(
            setting=Setting(
                place="Rural Hospital, Iowa",
                time="Winter 1995",
                weather_budget=["snow", "ice", "fog"],
            ),
            characters=[
                Character(
                    name="Dr. Katherine Walsh",
                    role="protagonist",
                    goal="Save the patient against impossible odds",
                    wound="Lost her mother to medical negligence",
                    quirks=["checks vitals obsessively", "quotes medical textbooks"],
                    diction_quirks=["technical medical jargon", "short declarative sentences"],
                ),
                Character(
                    name="Nurse Emma Rodriguez",
                    role="ally",
                    goal="Support Dr. Walsh",
                    quirks=["hums when nervous"],
                ),
            ],
            motifs=["time", "snow", "light", "distance"],
            imagery_palette=[
                "fluorescent lights",
                "beeping monitors",
                "sterile corridors",
                "frost patterns",
                "ambulance sirens",
            ],
        ),
        form=Form(
            beat_map=[
                BeatSpec(
                    id="cold_open",
                    target_words=100,
                    function="hook - establish tone and urgency",
                    cadence="short",
                    summary="Emergency call arrives on quiet night shift"
                ),
                BeatSpec(
                    id="rising_action",
                    target_words=120,
                    function="rising - complications mount",
                    cadence="mixed",
                    summary="Patient arrives in critical condition"
                ),
                BeatSpec(
                    id="crisis",
                    target_words=100,
                    function="crisis - moment of maximum tension",
                    cadence="short",
                    summary="Equipment fails at critical moment"
                ),
                BeatSpec(
                    id="climax",
                    target_words=90,
                    function="climax - decisive action",
                    cadence="short",
                    summary="Doctor makes life-or-death decision"
                ),
                BeatSpec(
                    id="resolution",
                    target_words=80,
                    function="resolution - consequences unfold",
                    cadence="long",
                    summary="Aftermath and reflection"
                ),
            ],
        ),
    )
    
    # Create a sample draft (realistic short story)
    draft = {
        "text": """
The call came at 3 AM. I was alone in the ER, Emma humming at the nurses' station.

"Cardiac arrest en route," dispatch said. "ETA four minutes."

I checked the defibrillator. The battery light blinked amber. We'd requisitioned a replacement three weeks ago.

The ambulance pulled in, snow swirling in its wake. The paramedic's face told me everything. "Forty-two-year-old male. V-fib. We've shocked him twice."

I looked at Emma. She'd stopped humming.

The monitors screamed. The defibrillator's battery died mid-charge. I thought of my mother, dying while doctors checked insurance forms.

"Manual compressions," I said. "We keep going."

Emma's hands moved in perfect rhythm. The fluorescent lights flickered, and for a moment I saw frost patterns on the window, beautiful and terrible.

At 3:47 AM, his heart restarted. Emma started humming again.

Outside, the snow continued to fall.
""",
        "seeds": {"global": 137, "per_beat": [137, 138, 139, 140, 141]},
    }
    
    # Create digest (simplified for demo)
    digest = ExemplarDigest(
        meta=DigestMeta(
            source="Emergency by Denis Johnson",
            tokens=2500,
            paragraphs=65,
        ),
    )
    
    # Create different exemplar text (for overlap check)
    exemplar_text = """
A man walked into the bar. The music was loud. He ordered a drink.

Outside, the city continued its endless noise. Inside, silence hung heavy between them.

She remembered the summer they met, hot asphalt and distant thunder. Now winter had come.

The clock ticked toward midnight. Decisions had to be made.

In the end, nothing changed. Everything changed.
""" * 20  # Make it longer to simulate realistic exemplar
    
    # Create generation config
    config = GenerationConfig(
        seed=137,
        num_candidates=4,
        objective_weights={
            "stylefit": 0.3,
            "formfit": 0.3,
            "coherence": 0.25,
            "freshness": 0.1,
            "cadence": 0.05,
        },
    )
    
    print("📊 Running evaluation suite...")
    print()
    
    # Run evaluation
    report = evaluate_draft(
        draft=draft,
        spec=spec,
        digest=digest,
        exemplar_text=exemplar_text,
        config=config,
        run_id="demo_run_001",
        candidate_id="demo_candidate_001",
        use_llm_stylefit=use_llm,
    )
    
    # Display results
    print("=" * 80)
    print("EVALUATION RESULTS")
    print("=" * 80)
    print()
    
    print(f"Run ID: {report.run_id}")
    print(f"Candidate ID: {report.candidate_id}")
    print(f"Pass/Fail: {'✅ PASS' if report.pass_fail else '❌ FAIL'}")
    print()
    
    print("SCORES:")
    print(f"  Overall:         {report.scores.overall:.3f}")
    print(f"  Stylefit:        {report.scores.stylefit:.3f}")
    print(f"  Formfit:         {report.scores.formfit:.3f}")
    print(f"  Coherence:       {report.scores.coherence:.3f}")
    print(f"  Freshness:       {report.scores.freshness:.3f}")
    print(f"  Cadence:         {report.scores.cadence:.3f}")
    print(f"  Motif Coverage:  {report.scores.motif_coverage:.3f}")
    print()
    
    print("OVERLAP GUARD:")
    print(f"  Max N-gram:      {report.scores.overlap_guard.max_ngram}")
    print(f"  Overlap %:       {report.scores.overlap_guard.overlap_pct:.1%}")
    print()
    
    print("LENGTH METRICS:")
    print(f"  Words:           {report.length['words']}")
    print(f"  Paragraphs:      {report.length['paragraphs']}")
    print()
    
    if report.per_beat:
        print("PER-BEAT SCORES:")
        for beat in report.per_beat:
            print(f"  {beat.id:20s} Stylefit: {beat.stylefit:.3f}  Formfit: {beat.formfit:.3f}")
            if beat.notes:
                # Truncate long notes
                notes = beat.notes[:80] + "..." if len(beat.notes) > 80 else beat.notes
                print(f"    → {notes}")
        print()
    
    if report.red_flags:
        print("⚠️  RED FLAGS:")
        for flag in report.red_flags:
            print(f"  • {flag}")
        print()
    
    if report.guardrail_failures:
        print("🚫 GUARDRAIL FAILURES:")
        for failure in report.guardrail_failures:
            print(f"  • {failure}")
        print()
    
    if report.tuning_suggestions:
        print("💡 TUNING SUGGESTIONS:")
        for i, suggestion in enumerate(report.tuning_suggestions[:5], 1):  # Show max 5
            print(f"  {i}. {suggestion.action.upper()} {suggestion.param} by {suggestion.by:.2f}")
            print(f"     Reason: {suggestion.reason}")
        if len(report.tuning_suggestions) > 5:
            print(f"  ... and {len(report.tuning_suggestions) - 5} more")
        print()
    
    # Save report
    print("💾 Saving evaluation report...")
    saved_path = save_eval_report(report, output_dir="runs")
    print(f"   Saved to: {saved_path}")
    print()
    
    # Show JSON excerpt
    print("📄 Report JSON (excerpt):")
    report_dict = json.loads(report.model_dump_json(by_alias=True, indent=2))
    excerpt = {
        "schema": report_dict["schema"],
        "run_id": report_dict["run_id"],
        "scores": report_dict["scores"],
        "pass_fail": report_dict["pass_fail"],
    }
    print(json.dumps(excerpt, indent=2))
    print()
    
    print("=" * 80)
    print("Demo complete!")
    print()
    
    if not use_llm:
        print("💡 Tip: Run with --use-llm flag to use real LLM for stylefit evaluation")
        print("   (requires OPENAI_API_KEY environment variable)")
    
    print()


if __name__ == "__main__":
    main()
