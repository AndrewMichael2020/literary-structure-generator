"""
Evaluation Orchestrator

Main entry point for evaluating generated drafts.
Orchestrates all evaluators and produces EvalReport@2.

Workflow:
1. Run all heuristic evaluators
2. Run optional LLM stylefit
3. Aggregate scores with weights
4. Identify red flags
5. Analyze drift vs spec
6. Generate tuning suggestions
7. Create EvalReport@2
"""

import hashlib
import os
from pathlib import Path
from typing import Dict, List, Optional

from literary_structure_generator.evaluators.cadence_pacing import evaluate_cadence_pacing
from literary_structure_generator.evaluators.coherence_graph_fit import (
    evaluate_coherence_graph_fit,
)
from literary_structure_generator.evaluators.formfit import evaluate_formfit
from literary_structure_generator.evaluators.motif_imagery_coverage import (
    evaluate_motif_imagery_coverage,
)
from literary_structure_generator.evaluators.overlap_guard_eval import (
    evaluate_overlap_guard,
)
from literary_structure_generator.evaluators.stylefit_llm import evaluate_stylefit_llm
from literary_structure_generator.evaluators.stylefit_rules import (
    evaluate_stylefit_rules,
)
from literary_structure_generator.models.eval_report import (
    DriftItem,
    EvalReport,
    OverlapGuard,
    PerBeatScore,
    Repro,
    Scores,
    TuningSuggestion,
)
from literary_structure_generator.models.exemplar_digest import ExemplarDigest
from literary_structure_generator.models.generation_config import GenerationConfig
from literary_structure_generator.models.story_spec import StorySpec


def run_all_evaluators(
    text: str,
    spec: StorySpec,
    digest: ExemplarDigest,
    exemplar_text: str,
    config: GenerationConfig,
    use_llm_stylefit: bool = False,
) -> Dict[str, any]:
    """
    Run all evaluation metrics.
    
    Args:
        text: Generated text to evaluate
        spec: StorySpec used for generation
        digest: ExemplarDigest for comparison
        exemplar_text: Original exemplar text (for overlap check)
        config: GenerationConfig used
        use_llm_stylefit: Whether to use LLM stylefit (default False for tests)
        
    Returns:
        Dictionary with all metric results
    """
    results = {}
    
    # Run heuristic stylefit
    results['stylefit_rules'] = evaluate_stylefit_rules(text, spec)
    
    # Run formfit
    results['formfit'] = evaluate_formfit(text, spec)
    
    # Run coherence
    results['coherence'] = evaluate_coherence_graph_fit(text)
    
    # Run motif/imagery coverage
    results['motif_coverage'] = evaluate_motif_imagery_coverage(text, spec, digest)
    
    # Run cadence/pacing
    results['cadence'] = evaluate_cadence_pacing(text, spec)
    
    # Run overlap guard
    results['overlap_guard'] = evaluate_overlap_guard(text, exemplar_text)
    
    # Run LLM stylefit (optional)
    results['stylefit_llm'] = evaluate_stylefit_llm(text, spec, use_llm=use_llm_stylefit)
    
    return results


def aggregate_scores(
    results: Dict[str, any],
    weights: Dict[str, float],
    use_llm_stylefit: bool = False,
) -> Scores:
    """
    Aggregate evaluation results into Scores object.
    
    Args:
        results: Dictionary of evaluation results
        weights: Dictionary of metric weights
        use_llm_stylefit: Whether LLM stylefit was used
        
    Returns:
        Scores object
    """
    # Extract individual scores
    stylefit_rules_score = results['stylefit_rules']['overall']
    formfit_score = results['formfit']['overall']
    coherence_score = results['coherence']['overall']
    motif_coverage_score = results['motif_coverage']['overall']
    cadence_score = results['cadence']['overall']
    
    # Combine stylefit scores
    if use_llm_stylefit and results['stylefit_llm']['overall'] is not None:
        # Blend heuristic and LLM stylefit
        llm_score = results['stylefit_llm']['overall']
        stylefit_score = (stylefit_rules_score * 0.4 + llm_score * 0.6)
    else:
        stylefit_score = stylefit_rules_score
    
    # Overlap guard (freshness)
    overlap_result = results['overlap_guard']
    if overlap_result['pass']:
        freshness_score = 1.0
    else:
        # Penalize based on violations
        freshness_score = max(0.0, 1.0 - len(overlap_result['violations']) * 0.3)
    
    # Dialogue balance (from stylefit_rules)
    dialogue_balance_score = results['stylefit_rules']['dialogue_ratio']
    
    # Calculate weighted overall score
    overall_components = {
        'stylefit': stylefit_score * weights.get('stylefit', 0.3),
        'formfit': formfit_score * weights.get('formfit', 0.3),
        'coherence': coherence_score * weights.get('coherence', 0.25),
        'freshness': freshness_score * weights.get('freshness', 0.1),
        'cadence': cadence_score * weights.get('cadence', 0.05),
    }
    
    overall_score = sum(overall_components.values())
    
    # Create OverlapGuard object
    overlap_guard = OverlapGuard(
        max_ngram=overlap_result['max_ngram'],
        overlap_pct=overlap_result['overlap_pct']
    )
    
    # Create Scores object
    scores = Scores(
        overall=overall_score,
        stylefit=stylefit_score,
        formfit=formfit_score,
        coherence=coherence_score,
        freshness=freshness_score,
        overlap_guard=overlap_guard,
        valence_arc_fit=0.0,  # Not implemented in this phase
        cadence=cadence_score,
        dialogue_balance=dialogue_balance_score,
        motif_coverage=motif_coverage_score,
    )
    
    return scores


def extract_per_beat_scores(results: Dict[str, any], spec: StorySpec) -> List[PerBeatScore]:
    """
    Extract per-beat scores from formfit results.
    
    Args:
        results: Dictionary of evaluation results
        spec: StorySpec with beat map
        
    Returns:
        List of PerBeatScore objects
    """
    per_beat_scores = []
    
    formfit_result = results['formfit']
    per_beat_length = formfit_result.get('per_beat_length', [])
    per_beat_function = formfit_result.get('per_beat_function', [])
    
    for i, beat_spec in enumerate(spec.form.beat_map):
        # Get length score
        if i < len(per_beat_length):
            length_data = per_beat_length[i]
            length_score = length_data['score']
            length_note = f"Target: {length_data['target_words']}w, Actual: {length_data['actual_words']}w"
        else:
            length_score = 0.5
            length_note = "No length data"
        
        # Get function score
        if i < len(per_beat_function):
            function_data = per_beat_function[i]
            function_score = function_data['score']
            function_note = f"Function: {function_data['function']}, Matches: {function_data['keyword_matches']}"
        else:
            function_score = 0.5
            function_note = "No function data"
        
        # Combine
        beat_stylefit = (length_score + function_score) / 2
        notes = f"{length_note}; {function_note}"
        
        per_beat_scores.append(PerBeatScore(
            id=beat_spec.id,
            stylefit=beat_stylefit,
            formfit=length_score,
            notes=notes
        ))
    
    return per_beat_scores


def identify_red_flags(results: Dict[str, any], scores: Scores) -> List[str]:
    """
    Identify quality red flags from evaluation results.
    
    Args:
        results: Dictionary of evaluation results
        scores: Aggregated scores
        
    Returns:
        List of red flag descriptions
    """
    red_flags = []
    
    # Check overlap guard
    overlap_result = results['overlap_guard']
    if not overlap_result['pass']:
        for violation in overlap_result['violations']:
            red_flags.append(f"Overlap violation: {violation}")
    
    # Check person/tense consistency
    stylefit_result = results['stylefit_rules']
    if stylefit_result['person_consistency'] < 0.7:
        red_flags.append(f"POV drift detected (score: {stylefit_result['person_consistency']:.2f})")
    
    if stylefit_result['tense_consistency'] < 0.7:
        red_flags.append(f"Tense inconsistency (score: {stylefit_result['tense_consistency']:.2f})")
    
    # Check dialogue ratio
    if stylefit_result['dialogue_ratio'] < 0.7:
        red_flags.append(f"Dialogue ratio drift (score: {stylefit_result['dialogue_ratio']:.2f})")
    
    # Check clean mode
    if stylefit_result['clean_mode'] < 1.0:
        red_flags.append("Clean mode violation: profanity detected")
    
    # Check coherence issues
    coherence_result = results['coherence']
    if coherence_result['issues']:
        for issue in coherence_result['issues']:
            red_flags.append(f"Coherence: {issue}")
    
    # Check overall score
    if scores.overall < 0.5:
        red_flags.append(f"Overall score below acceptable threshold: {scores.overall:.2f}")
    
    return red_flags


def analyze_drift(
    results: Dict[str, any],
    spec: StorySpec,
    text: str
) -> List[DriftItem]:
    """
    Analyze drift from specification.
    
    Args:
        results: Dictionary of evaluation results
        spec: StorySpec with targets
        text: Generated text (for calculating actual values)
        
    Returns:
        List of DriftItem objects
    """
    drift_items = []
    
    # Calculate actual dialogue ratio
    from literary_structure_generator.evaluators.stylefit_rules import (
        calculate_dialogue_ratio,
        calculate_avg_sentence_length,
    )
    
    target_dialogue_ratio = spec.form.dialogue_ratio
    actual_dialogue_ratio = calculate_dialogue_ratio(text)
    
    drift_items.append(DriftItem(
        field="dialogue_ratio",
        target=target_dialogue_ratio,
        actual=actual_dialogue_ratio,
        delta=actual_dialogue_ratio - target_dialogue_ratio
    ))
    
    # Add sentence length drift
    target_sentence_len = spec.voice.syntax.avg_sentence_len
    actual_sentence_len = calculate_avg_sentence_length(text)
    
    drift_items.append(DriftItem(
        field="avg_sentence_len",
        target=float(target_sentence_len),
        actual=actual_sentence_len,
        delta=actual_sentence_len - target_sentence_len
    ))
    
    return drift_items


def generate_tuning_suggestions(
    results: Dict[str, any],
    scores: Scores,
    spec: StorySpec,
    config: GenerationConfig,
) -> List[TuningSuggestion]:
    """
    Generate tuning suggestions for next iteration.
    
    Args:
        results: Dictionary of evaluation results
        scores: Aggregated scores
        spec: StorySpec used
        config: GenerationConfig used
        
    Returns:
        List of TuningSuggestion objects
    """
    suggestions = []
    
    # Suggestion based on formfit
    formfit_result = results['formfit']
    if formfit_result['beat_length_adherence'] < 0.7:
        # Suggest adjusting beat lengths
        per_beat = formfit_result.get('per_beat_length', [])
        for beat_data in per_beat:
            if beat_data['score'] < 0.7:
                deviation_words = beat_data['actual_words'] - beat_data['target_words']
                if abs(deviation_words) > 50:
                    action = "decrease" if deviation_words > 0 else "increase"
                    suggestions.append(TuningSuggestion(
                        param=f"{beat_data['beat_id']}.target_words",
                        action=action,
                        by=abs(deviation_words) * 0.5,
                        reason=f"Beat length drift: {deviation_words:+d} words"
                    ))
    
    # Suggestion based on stylefit
    stylefit_result = results['stylefit_rules']
    if stylefit_result['sentence_length'] < 0.7:
        suggestions.append(TuningSuggestion(
            param="syntax.avg_sentence_len",
            action="adjust",
            by=2.0,
            reason="Sentence length doesn't match target"
        ))
    
    # Suggestion based on temperature (if model supports it)
    if scores.overall < 0.6:
        # Check if model supports temperature
        # For now, suggest generic temperature adjustment
        suggestions.append(TuningSuggestion(
            param="temperature",
            action="decrease",
            by=0.1,
            reason=f"Low overall score ({scores.overall:.2f}), try more conservative generation"
        ))
    
    # Suggestion based on motif coverage
    motif_result = results['motif_coverage']
    if motif_result['overall_coverage'] < 0.6:
        suggestions.append(TuningSuggestion(
            param="motif_quota",
            action="increase",
            by=0.2,
            reason=f"Low motif coverage ({motif_result['overall_coverage']:.2f})"
        ))
    
    if motif_result['overall_overuse_penalty'] > 0.3:
        suggestions.append(TuningSuggestion(
            param="motif_quota",
            action="decrease",
            by=0.15,
            reason=f"Motif overuse detected (penalty: {motif_result['overall_overuse_penalty']:.2f})"
        ))
    
    return suggestions


def create_repro_info(config: GenerationConfig) -> Repro:
    """
    Create reproducibility information.
    
    Args:
        config: GenerationConfig used
        
    Returns:
        Repro object
    """
    # Get git commit (if available)
    git_commit = os.getenv('GIT_COMMIT', 'unknown')
    
    # Model info from config
    model = "mock"  # Default
    temp = config.per_beat_generation.temperature[0] if config.per_beat_generation.temperature else 0.0
    
    return Repro(
        git_commit=git_commit,
        model=model,
        model_temp=temp
    )


def evaluate_draft(
    draft: dict,
    spec: StorySpec,
    digest: ExemplarDigest,
    exemplar_text: str = "",
    config: Optional[GenerationConfig] = None,
    run_id: str = "eval_001",
    candidate_id: str = "cand_001",
    use_llm_stylefit: bool = False,
) -> EvalReport:
    """
    Main entry point: evaluate a generated draft.
    
    Args:
        draft: Draft dictionary with 'text' key
        spec: StorySpec used for generation
        digest: ExemplarDigest for comparison
        exemplar_text: Original exemplar text (for overlap check)
        config: GenerationConfig used (optional)
        run_id: Unique run identifier
        candidate_id: Candidate identifier
        use_llm_stylefit: Whether to use LLM stylefit (default False for offline tests)
        
    Returns:
        EvalReport@2 object
    """
    # Extract text from draft
    text = draft.get('text', '')
    
    # Use default config if not provided
    if config is None:
        config = GenerationConfig()
    
    # Calculate config hash
    config_hash = hashlib.md5(config.model_dump_json().encode()).hexdigest()[:8]
    
    # Run all evaluators
    results = run_all_evaluators(
        text=text,
        spec=spec,
        digest=digest,
        exemplar_text=exemplar_text,
        config=config,
        use_llm_stylefit=use_llm_stylefit,
    )
    
    # Aggregate scores
    scores = aggregate_scores(results, config.objective_weights, use_llm_stylefit)
    
    # Extract per-beat scores
    per_beat = extract_per_beat_scores(results, spec)
    
    # Identify red flags
    red_flags = identify_red_flags(results, scores)
    
    # Analyze drift
    drift_items = analyze_drift(results, spec, text)
    
    # Generate tuning suggestions
    tuning_suggestions = generate_tuning_suggestions(results, scores, spec, config)
    
    # Create repro info
    repro = create_repro_info(config)
    
    # Check pass/fail
    overlap_passed = results['overlap_guard']['pass']
    score_passed = scores.overall >= 0.5
    pass_fail = overlap_passed and score_passed
    
    # Calculate length metrics
    word_count = len(text.split())
    paragraph_count = len([p for p in text.split('\n\n') if p.strip()])
    
    # Create EvalReport
    report = EvalReport(
        run_id=run_id,
        candidate_id=candidate_id,
        config_hash=config_hash,
        seeds={
            'global': config.seed,
            'per_beat': draft.get('seeds', {}).get('per_beat', [])
        },
        length={
            'words': word_count,
            'paragraphs': paragraph_count,
        },
        scores=scores,
        per_beat=per_beat,
        red_flags=red_flags,
        guardrail_failures=results['overlap_guard']['violations'] if not overlap_passed else [],
        drift_vs_spec=drift_items,
        tuning_suggestions=tuning_suggestions,
        pass_fail=pass_fail,
        notes=f"Evaluation completed. {len(red_flags)} red flags identified.",
        repro=repro,
    )
    
    return report


def save_eval_report(report: EvalReport, output_dir: str = "runs") -> Path:
    """
    Save EvalReport to runs directory.
    
    Args:
        report: EvalReport to save
        output_dir: Output directory
        
    Returns:
        Path to saved file
    """
    output_path = Path(output_dir) / report.run_id
    output_path.mkdir(parents=True, exist_ok=True)
    
    filepath = output_path / f"{report.candidate_id}_eval.json"
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(report.model_dump_json(indent=2, by_alias=True))
    
    return filepath
