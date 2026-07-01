#!/usr/bin/env python3
"""
Healthcheck for Literary Structure Generator

This script performs basic sanity tests on key components of the app.
It checks that core modules load, verifies basic functionality,
and prints status messages that can help you ensure the app runs well.
"""

def check_llm_router():
    try:
        from literary_structure_generator.llm.router import get_client, get_params
        client = get_client("mock_test")
        params = get_params("mock_test")
        print("LLM Router: PASS")
    except Exception as e:
        print("LLM Router: FAIL ->", e)

def check_beat_drafter():
    try:
        from literary_structure_generator.generation.beat_drafter import build_beat_prompt
        try:
            # We pass dummy values; NotImplementedError is expected.
            build_beat_prompt(None, "beat1")
        except NotImplementedError:
            print("Beat Drafter: NotImplementedError as expected")
        except Exception as e:
            print("Beat Drafter: FAIL ->", e)
    except Exception as e:
        print("Beat Drafter module: FAIL ->", e)

def check_spec_synthesizer():
    try:
        from literary_structure_generator.spec.synthesizer import synthesize_spec
        # Since synthesize_spec requires complex objects, we simply test that it loads.
        print("Spec Synthesizer: Module loaded")
    except Exception as e:
        print("Spec Synthesizer: FAIL ->", e)

def main():
    print("Running Healthcheck for Literary Structure Generator\n")
    check_llm_router()
    check_beat_drafter()
    check_spec_synthesizer()
    print("\nHealthcheck complete. (Note: Many functions are expected to raise NotImplementedError.)")

if __name__ == '__main__':
    main()
