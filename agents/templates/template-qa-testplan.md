# QA Test Plan Template

## 📋 Document Metadata

| Field | Value |
|-------|-------|
| **Test Plan ID** | QA-XXX |
| **Title** | [Feature/System] Test Plan |
| **Author** | QA Engineer [Name] |
| **Feature ID** | [FEAT-XXX / PRD-XXX] |
| **Status** | DRAFT / REVIEW / APPROVED |
| **Version** | 1.0 |
| **Created** | YYYY-MM-DD |
| **Target Date** | YYYY-MM-DD |

---

## 🎯 Overview

### Scope
[What is being tested]

### Test Objectives
1. [Objective 1]
2. [Objective 2]
3. [Objective 3]

### In Scope
- [Feature/area 1]
- [Feature/area 2]

### Out of Scope
- [Feature/area not tested]

---

## 📋 Test Strategy

### Testing Levels
- [ ] **Unit Testing** - [Coverage target]
- [ ] **Integration Testing** - [Areas]
- [ ] **Functional Testing** - [Features]
- [ ] **Regression Testing** - [Scope]
- [ ] **Performance Testing** - [If applicable]
- [ ] **Security Testing** - [If applicable]
- [ ] **UX Testing** - [If applicable]

### Testing Approach
[Manual/Automated/Mixed with rationale]

### Test Environment
- URL: [Staging URL]
- Database: [Test data setup]
- Browser/Device Matrix: [List]

---

## ✅ Test Cases

### Feature: [Feature Name]

#### TC-001: [Test Case Title]
| Field | Value |
|-------|-------|
| **Priority** | P0 / P1 / P2 |
| **Type** | Functional / UI / API / Edge |

**Preconditions:**
- [Setup required]

**Steps:**
1. [Step 1]
2. [Step 2]
3. [Step 3]

**Expected Result:**
[What should happen]

**Test Data:**
[Specific data to use]

---

#### TC-002: [Test Case Title]
[Same format]

### Feature: [Another Feature]
[Same format]

---

## 🔄 Regression Test Suite

### Critical Path Tests
- [ ] [Critical test 1]
- [ ] [Critical test 2]
- [ ] [Critical test 3]

### Previous Feature Tests
- [ ] [Related feature test 1]
- [ ] [Related feature test 2]

---

## 🐛 Bug Tracking

### Bug Severity Definitions
| Severity | Definition | Example |
|----------|------------|---------|
| Blocker | Feature unusable | App crashes |
| Critical | Major functionality broken | Data loss |
| Major | Significant impact | Workaround exists |
| Minor | Low impact | Cosmetic issue |
| Trivial | Minimal impact | Typo |

### Bug Report Template
```
ID: BUG-XXX
Title: [Brief description]
Severity: [Blocker/Critical/Major/Minor/Trivial]
Steps to Reproduce:
1. [Step]
Expected: [Expected result]
Actual: [Actual result]
Environment: [Browser/Device]
```

---

## 📊 Test Execution

### Test Schedule

| Phase | Activities | Duration | Owner |
|-------|------------|----------|-------|
| Preparation | Setup environment | X hours | QA |
| Execution | Run test cases | X hours | QA |
| Regression | Regression tests | X hours | QA |
| Sign-off | Final approval | X hours | QA Lead |

### Entry Criteria
- [ ] Code deployed to staging
- [ ] Unit tests passing
- [ ] Test data prepared
- [ ] Environment ready

### Exit Criteria
- [ ] All P0 tests passed
- [ ] No open Blocker/Critical bugs
- [ ] Regression tests passed
- [ ] Sign-off obtained

---

## 📈 Test Metrics

### To Track
| Metric | Target | Actual |
|--------|--------|--------|
| Test Case Coverage | X% | |
| Test Execution Rate | X% | |
| Pass Rate | >95% | |
| Defect Density | <X/100 LOC | |

---

## ⚠️ Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| [Risk 1] | High/Med/Low | [Strategy] |
| [Risk 2] | High/Med/Low | [Strategy] |

---

## 📋 Definition of Done

- [ ] All P0/P1 test cases executed
- [ ] No Blocker/Critical bugs open
- [ ] Regression tests pass
- [ ] Test results documented
- [ ] Sign-off obtained

---

## 📝 Handoff Notes

### For Developer
- [Bugs found with severity]
- [Areas needing attention]
- [Test data that might be useful]

### For PM
- [Quality assessment]
- [Risk areas]
- [Recommendation for release]

### Status Summary
- **Tests Passed:** [X/Y]
- **Bugs Found:** [Count by severity]
- **Known Issues:** [List]
- **Release Recommendation:** [GO / GO with reservations / NO GO]

---

## 📎 Appendix

### Test Data
[Sample data for testing]

### Reference Documents
- [PRD]
- [Tech Spec]
- [Previous test plans]

---

*Template Version: 1.0*  
*Last Updated: 2026-02-02*
