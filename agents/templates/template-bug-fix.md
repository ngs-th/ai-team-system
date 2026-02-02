# Bug Fix Task Template

## Task Metadata
| Field | Value |
|-------|-------|
| **Bug ID** | BUG-XXX |
| **Title** | [Brief description of the bug] |
| **Assignee** | [Agent Name] |
| **Priority** | 🔴 Critical / 🟠 High / 🟡 Medium / 🟢 Low |
| **Severity** | 🔴 Blocker / 🟠 Major / 🟡 Minor / 🟢 Trivial |
| **Due Date** | YYYY-MM-DD |
| **Reported By** | [Who found the bug] |
| **Reported Date** | YYYY-MM-DD |
| **Affected Version** | [Version where bug exists] |
| **Fixed Version** | [Version where fix will be released] |

---

## Context / Background

### Bug Summary
[One-paragraph summary of the issue]

### Steps to Reproduce
1. [Step 1 - e.g., "Navigate to /settings/profile"]
2. [Step 2 - e.g., "Click 'Update Email' button"]
3. [Step 3 - e.g., "Enter invalid email format"]
4. [Step 4 - Observe error]

### Expected Behavior
[What should happen]

### Actual Behavior
[What actually happens]

### Environment
| Attribute | Details |
|-----------|---------|
| **Browser** | [e.g., Chrome 120, Safari 17] |
| **OS** | [e.g., macOS 14.2, Windows 11] |
| **Device** | [e.g., Desktop, iPhone 15 Pro] |
| **App Version** | [e.g., v2.3.1] |
| **Environment** | [Production / Staging / Development] |

### Screenshots / Evidence
[Attach screenshots, screen recordings, or log snippets]

```
[Error logs or stack traces here]
```

### Related Issues
- [Link to related bug reports]
- [Link to customer support tickets]
- [Link to Slack threads or discussions]

---

## Root Cause Analysis

### Initial Hypothesis
[What do we think is causing this?]

### Investigation Notes
- [ ] Checked error logs: [findings]
- [ ] Reviewed recent commits: [relevant changes]
- [ ] Reproduced locally: [Yes/No - notes]
- [ ] Database state examined: [findings]

### Root Cause
[The actual cause of the bug - be specific]

### Impact Assessment
- **Users Affected**: [Estimated number or "All users" / "Specific segment"]
- **Frequency**: [How often does this occur?]
- **Workaround Available**: [Yes/No - describe if yes]
- **Data Loss Risk**: [Yes/No - explain if yes]

---

## Fix Requirements / Acceptance Criteria

### Fix Verification
- [ ] Bug is reproducible before the fix
- [ ] Bug is NOT reproducible after the fix
- [ ] Fix handles all identified edge cases
- [ ] No regressions introduced

### Test Scenarios
- [ ] [Test case 1 - the original reproduction steps]
- [ ] [Test case 2 - variation of the scenario]
- [ ] [Test case 3 - edge case]
- [ ] [Test case 4 - regression test for related functionality]

### Regression Testing
- [ ] [Related feature 1 still works]
- [ ] [Related feature 2 still works]
- [ ] [API endpoints still respond correctly]
- [ ] [Database operations still function]

---

## Technical Notes

### Files to Modify
```
[path/to/file.ts] - [Specific change needed]
[path/to/file.css] - [Styling fix if applicable]
```

### Proposed Solution
[Describe the technical approach to fixing the bug]

### Alternative Solutions Considered
| Approach | Pros | Cons | Decision |
|----------|------|------|----------|
| [Option 1] | [Pros] | [Cons] | [Selected/Rejected] |
| [Option 2] | [Pros] | [Cons] | [Selected/Rejected] |

### Database Changes (if applicable)
- [ ] Migration needed: [Yes/No - details]
- [ ] Data cleanup needed: [Yes/No - details]
- [ ] Rollback plan: [How to undo if needed]

### Hotfix Considerations
- [ ] This is a hotfix for production: [Yes/No]
- [ ] Hotfix branch created from: [tag/commit]
- [ ] Cherry-pick to main needed: [Yes/No]

---

## Implementation Checklist

### Phase 1: Investigation
- [ ] Bug reproduced in local environment
- [ ] Root cause identified and documented above
- [ ] Fix approach validated

### Phase 2: Implementation
- [ ] Create branch: `fix/BUG-XXX-brief-description`
- [ ] Implement fix
- [ ] Add/update unit tests
- [ ] Add regression test if applicable

### Phase 3: Testing
- [ ] Fix verified against reproduction steps
- [ ] Edge cases tested
- [ ] Regression tests pass
- [ ] Code review completed

### Phase 4: Deployment
- [ ] Merged to main/develop branch
- [ ] Deployed to staging
- [ ] Verified in staging environment
- [ ] Deployed to production (if hotfix)
- [ ] Monitoring for 24-48 hours

---

## Definition of Done

- [ ] Root cause documented
- [ ] Fix implemented and tested
- [ ] Reproduction steps verified as fixed
- [ ] Regression tests added
- [ ] No new warnings or errors introduced
- [ ] Code review approved
- [ ] Deployed to production (if applicable)
- [ ] Bug report closed with resolution notes
- [ ] Post-mortem scheduled (if critical/severe)

---

## Handoff Notes

### For Code Reviewer
- [Critical areas to review]
- [Why this fix approach was chosen]
- [Any potential side effects to watch for]

### For QA/Testing
- [Specific scenarios to verify]
- [Browsers/environments to test]
- [Performance impact to check]

### For DevOps (if hotfix)
- [Deployment urgency level]
- [Any special deployment steps]
- [Monitoring alerts to watch]

### For Support Team
- [Customer communication template if needed]
- [Workaround until fix is deployed]
- [Timeline for fix availability]

---

## Progress Log

| Date | Agent | Action | Notes |
|------|-------|--------|-------|
| YYYY-MM-DD | [Name] | Bug reported | [Initial report] |
| YYYY-MM-DD | [Name] | Investigation started | [Initial findings] |
| YYYY-MM-DD | [Name] | Root cause identified | [Cause description] |
| YYYY-MM-DD | [Name] | Fix implemented | [PR link] |
| YYYY-MM-DD | [Name] | Fix deployed | [Version deployed] |

---

## References
- [Original bug report link]
- [Error logs link]
- [Related PR that introduced the bug (if known)]
- [Slack discussion link]
