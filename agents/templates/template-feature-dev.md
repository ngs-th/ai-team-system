# Feature Development Task Template

## Task Metadata
| Field | Value |
|-------|-------|
| **Task ID** | FEAT-XXX |
| **Title** | [Feature Name] |
| **Assignee** | [Agent Name] |
| **Priority** | 🔴 High / 🟡 Medium / 🟢 Low |
| **Due Date** | YYYY-MM-DD |
| **Estimated Effort** | [X hours/days] |
| **Parent PRD** | [Link to PRD if applicable] |
| **Related Issues** | [Links to related bugs/tasks] |

---

## Context / Background

### Problem Statement
[Describe the problem or opportunity this feature addresses]

### User Story
As a [type of user], I want [goal] so that [benefit].

### Current State
[Describe the current implementation/state if modifying existing code]

### Target State
[Describe what success looks like]

---

## Requirements / Acceptance Criteria

### Functional Requirements
- [ ] [Requirement 1 - specific, testable behavior]
- [ ] [Requirement 2 - specific, testable behavior]
- [ ] [Requirement 3 - specific, testable behavior]

### Non-Functional Requirements
- [ ] Performance: [e.g., "Page load < 2 seconds"]
- [ ] Security: [e.g., "All API calls require authentication"]
- [ ] Accessibility: [e.g., "WCAG 2.1 AA compliant"]
- [ ] Browser/Device Support: [e.g., "Chrome 90+, Safari 14+, mobile responsive"]

### Edge Cases to Handle
- [ ] [Edge case 1 - e.g., "Empty state when no data"]
- [ ] [Edge case 2 - e.g., "Network failure handling"]
- [ ] [Edge case 3 - e.g., "Large dataset pagination"]

---

## Technical Notes

### Architecture Overview
[Describe the high-level approach, diagrams if needed]

### Files to Modify/Create
```
[path/to/new/file.ts] - [Purpose]
[path/to/existing/file.ts] - [Modification reason]
```

### Dependencies
- **Add**: [New libraries/packages needed]
- **Update**: [Existing dependencies to upgrade]
- **Remove**: [Dependencies to clean up]

### API Changes
| Endpoint | Method | Change | Description |
|----------|--------|--------|-------------|
| /api/... | GET/POST/PUT/DELETE | Add/Modify/Remove | [Description] |

### Database Changes (if applicable)
- **New Tables**: [Table names and schemas]
- **Migrations**: [Migration file names]
- **Indexes**: [Performance optimization indexes]

### Testing Strategy
- **Unit Tests**: [What logic needs unit testing]
- **Integration Tests**: [What flows need integration testing]
- **E2E Tests**: [What user journeys need E2E coverage]

### Risks & Mitigations
| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| [Risk description] | High/Med/Low | High/Med/Low | [How to mitigate] |

---

## Implementation Checklist

### Phase 1: Setup & Design
- [ ] Read related PRD and existing codebase
- [ ] Create feature branch: `feat/FEAT-XXX-feature-name`
- [ ] Set up any new dependencies
- [ ] Write implementation plan in this doc

### Phase 2: Core Implementation
- [ ] [Specific implementation step 1]
- [ ] [Specific implementation step 2]
- [ ] [Specific implementation step 3]

### Phase 3: Testing
- [ ] Unit tests written and passing
- [ ] Integration tests written and passing
- [ ] Manual testing completed
- [ ] Edge cases tested

### Phase 4: Documentation
- [ ] Code comments added where needed
- [ ] README/API docs updated
- [ ] Changelog updated

### Phase 5: Review & Merge
- [ ] Self-review completed
- [ ] PR created with clear description
- [ ] All CI checks passing
- [ ] Code review approved
- [ ] Merged to main branch

---

## Definition of Done

- [ ] All acceptance criteria met
- [ ] Code follows project style guidelines
- [ ] Tests written with >80% coverage for new code
- [ ] No console errors or warnings
- [ ] Documentation updated
- [ ] Feature tested in staging environment
- [ ] Performance benchmarks met (if applicable)
- [ ] Security review passed (if applicable)
- [ ] Accessibility audit passed (if applicable)

---

## Handoff Notes

### For Code Reviewer
- [Key areas to focus on during review]
- [Any shortcuts taken that need scrutiny]
- [Performance considerations]

### For QA Team
- [Specific test scenarios to verify]
- [Environment setup requirements]
- [Known limitations or temporary workarounds]

### For DevOps/Deployment
- [Environment variables to set]
- [Database migrations to run]
- [Feature flags to configure]
- [Rollback procedures]

### For Documentation Team
- [User-facing changes to document]
- [Screenshots/diagrams needed]

---

## Progress Log

| Date | Agent | Action | Notes |
|------|-------|--------|-------|
| YYYY-MM-DD | [Name] | Task created | [Initial context] |
| YYYY-MM-DD | [Name] | [Action taken] | [Notes] |

---

## References
- [PRD Link]
- [Design Mockups]
- [API Documentation]
- [Related Issues/PRs]
