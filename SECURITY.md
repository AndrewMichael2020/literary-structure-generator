# Security Policy

## Reporting Security Vulnerabilities

We take security seriously. If you discover a security vulnerability, please report it by emailing the maintainers directly rather than opening a public issue.

**Please do not create public GitHub issues for security vulnerabilities.**

### Contact

- Email: [Create issue with "SECURITY" label for urgent matters]

### What to Include

When reporting a security vulnerability, please include:

1. Description of the vulnerability
2. Steps to reproduce the issue
3. Potential impact
4. Suggested fix (if available)

## Security Best Practices

### API Keys and Secrets

**Never commit API keys, tokens, or other secrets to the repository.**

- Use environment variables for sensitive data
- Copy `.env.example` to `.env` and add your secrets there
- `.env` is in `.gitignore` and will not be committed

### Environment Variables

The system uses the following environment variables for sensitive data:

```bash
# OpenAI API Key (optional - system defaults to mock client)
OPENAI_API_KEY=your-api-key-here

# Anthropic API Key (optional)
ANTHROPIC_API_KEY=your-api-key-here

# LLM Mode (real or mock)
LLM_MODE=mock
```

### Running Tests Offline

**All tests run offline by default** using the `MockClient` to ensure:

- No accidental API charges
- Reproducible test results
- Fast test execution
- No external dependencies

To run tests with real LLM providers:

1. Set environment variables for API keys
2. Update `llm/config/llm_routing.json` to use real providers
3. Be aware of API costs

### Content Safety

The system includes multiple safety mechanisms:

1. **Profanity Filtering**: Universal `[bleep]` replacement for profanity
2. **Anti-Plagiarism Guards**: 
   - Maximum n-gram overlap: 12 tokens
   - Overall overlap threshold: ≤3%
   - SimHash Hamming distance: ≥18
3. **Content Constraints**: Configurable via `AuthorProfile` and `StorySpec`

### Data Privacy

- **No verbatim exemplar text** is stored in artifacts
- Only structural features and patterns are extracted
- Generated content is stored in `runs/` directory
- Cache data in `runs/llm_cache.db` contains prompts and responses

### Recommendations

1. **Exemplar Texts**: Only use texts you have the rights to analyze
2. **Generated Content**: Review generated content before publishing
3. **API Keys**: Rotate API keys regularly
4. **Cache**: Clean up `runs/llm_cache.db` if it contains sensitive prompts
5. **Artifacts**: Do not share `runs/` directory if it contains sensitive data

## Security Updates

Security patches will be released as soon as possible after discovery. Update to the latest version regularly to ensure you have the latest security fixes.

### Dependency Security

- Dependabot is configured to automatically check for dependency vulnerabilities
- Update dependencies regularly using:
  ```bash
  pip install --upgrade -r requirements.txt
  pip install --upgrade -r requirements-dev.txt
  ```

### Code Scanning

- CodeQL security scanning is enabled on this repository
- Security alerts are reviewed and addressed promptly
- All PRs are scanned for security issues before merging

## Responsible Disclosure

We practice responsible disclosure:

1. Security issues are fixed before public announcement
2. Reporters are credited (if desired) in release notes
3. Users are notified of security updates through releases

## Known Limitations

### LLM Provider Security

When using real LLM providers (OpenAI, Anthropic):

- Prompts and responses may be logged by the provider
- Review provider privacy policies
- Use mock client for sensitive content

### Local Storage

- Artifacts in `runs/` are stored unencrypted
- Cache in `runs/llm_cache.db` is SQLite without encryption
- Decision logs in `decisions.jsonl` may contain prompts

### Profanity Filter

- The profanity filter is heuristic-based
- It may not catch all variants or context-specific profanity
- It uses a predefined list that can be extended

## Compliance

### Copyright

- Do not use copyrighted texts as exemplars without permission
- Generated content is derivative and subject to applicable law
- Anti-plagiarism guards help prevent verbatim copying

### Content Generation

- Generated content should be reviewed before publication
- The system is a tool; human oversight is required
- Profanity filtering maintains authenticity with `[bleep]` replacement

## Support

For security questions or concerns:

1. Check this security policy
2. Review the documentation
3. Contact maintainers via GitHub issues (non-sensitive matters)

Thank you for helping keep this project secure!
