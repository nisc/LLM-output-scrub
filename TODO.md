# TODO

**Effort:** 🟢 Quick wins | 🟡 Moderate work | 🔴 Major work

## Performance & Optimization
- **🟡** Optimize spaCy inferences: Currently processes each EM dash individually. Should process entire text once through spaCy pipeline and reuse linguistic annotations for all dashes.
- **🟡** Optimize app bundle: Reduce file size and memory usage

## Features & Functionality
- **🔴** Train classifier for smart character disambiguation (EM/EN dashes) instead of rule-based approach based on spaCy model inferences
- **🔴** Add support for other operating systems
- **🔴** Add support for other input languages
- **🟢** Use spaCy features for other context-dependent character replacements (e.g., EN dashes, beyond EM dashes)

## Testing & Quality
- **🟢** Add more diverse test cases based on real world LLM output