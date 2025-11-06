# Contributing to Literary Structure Generator

Thank you for your interest in contributing! This document provides guidelines and instructions for contributing to the project.

## Development Setup

### Prerequisites

- Python 3.9 or higher
- Git

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/AndrewMichael2020/literary-structure-generator.git
   cd literary-structure-generator
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```

4. **Download spaCy model**
   ```bash
   python -m spacy download en_core_web_sm
   ```

5. **Configure environment** (optional)
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

## Development Workflow

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=literary_structure_generator --cov-report=term-missing

# Run specific test file
pytest tests/test_profanity_filter.py

# Run specific test
pytest tests/test_profanity_filter.py::TestStructuralBleep::test_single_profanity
```

### Code Quality

#### Linting with Ruff

```bash
# Check for issues
ruff check literary_structure_generator/

# Auto-fix issues
ruff check --fix literary_structure_generator/
```

#### Formatting with Black

```bash
# Check formatting
black --check literary_structure_generator/

# Auto-format
black literary_structure_generator/
```

#### Type Checking with mypy

```bash
# Run type checking
mypy literary_structure_generator/
```

### Running the Full Quality Check

Before submitting a PR, run:

```bash
# Lint
ruff check literary_structure_generator/

# Format check
black --check literary_structure_generator/

# Type check
mypy literary_structure_generator/

# Run tests with coverage
pytest --cov=literary_structure_generator --cov-report=term-missing
```

## Making Changes

### Branch Naming

- Feature branches: `feature/description`
- Bug fixes: `fix/description`
- Documentation: `docs/description`

### Commit Messages

Follow conventional commits:

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

Examples:
```
feat(profanity): add universal [bleep] filtering

fix(llm): handle cache miss gracefully

docs(architecture): add Mermaid diagrams
```

### Pull Request Process

1. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**
   - Write clean, well-documented code
   - Follow existing code style
   - Add tests for new functionality
   - Update documentation as needed

3. **Test your changes**
   ```bash
   pytest
   ruff check literary_structure_generator/
   black --check literary_structure_generator/
   ```

4. **Commit your changes**
   ```bash
   git add .
   git commit -m "feat(component): description of changes"
   ```

5. **Push to your fork**
   ```bash
   git push origin feature/your-feature-name
   ```

6. **Create a Pull Request**
   - Provide a clear description of the changes
   - Reference any related issues
   - Ensure CI checks pass
   - Request review from maintainers

### PR Requirements

- All tests must pass
- Code coverage should not decrease (aim for ≥95%)
- Code must pass linting (ruff)
- Code must be formatted (black)
- Type hints should be added for new functions
- Documentation must be updated for new features

## Code Style Guidelines

### Python Style

- Follow PEP 8
- Use type hints for function signatures
- Maximum line length: 100 characters
- Use docstrings for all public functions, classes, and modules

### Docstring Format

```python
def example_function(param1: str, param2: int) -> bool:
    """
    Brief description of the function.

    Longer description if needed, explaining the function's purpose,
    behavior, and any important details.

    Args:
        param1: Description of param1
        param2: Description of param2

    Returns:
        Description of return value

    Raises:
        ValueError: When param2 is negative
    """
    pass
```

### Testing Guidelines

- Write tests for all new features
- Use descriptive test names that explain what is being tested
- Use pytest fixtures for common test setup
- Aim for high test coverage (≥95%)
- Test edge cases and error conditions

### Documentation

- Update README.md for significant changes
- Add/update docstrings for new code
- Update architecture.md for architectural changes
- Include examples in docstrings when helpful

## Project Structure

```
literary-structure-generator/
├── literary_structure_generator/  # Main package
│   ├── digest/                   # Exemplar analysis
│   ├── spec/                     # StorySpec synthesis
│   ├── generation/               # Draft generation
│   ├── evaluation/               # Evaluation metrics
│   ├── optimization/             # Optimization loop
│   ├── llm/                      # LLM integration
│   ├── models/                   # Pydantic models
│   ├── utils/                    # Utilities
│   └── evaluators/               # Evaluator implementations
├── tests/                        # Test suite
├── docs/                         # Documentation
├── examples/                     # Example scripts
├── prompts/                      # LLM prompt templates
└── runs/                         # Execution artifacts
```

## Questions or Issues?

- Check existing issues before creating a new one
- Use issue templates when available
- Provide as much detail as possible
- Include reproduction steps for bugs

## Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Help others learn and grow
- Follow project guidelines

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
