# PEDAC Walkthrough: Comparing Version Numbers

## Explanation

This lesson works through one problem, **comparing two version numbers**, using every step of the PEDAC process:

1. **Understand the Problem and Requirements** – turn the description and examples into explicit rules
2. **Create Examples / Test Cases** – write generic cases and edge cases, then use them to fix gaps in the requirements
3. **Data Structure and Algorithm** – choose how to represent the data and write steps to produce the output
4. **Translate Algorithm Steps Into Code**
5. **Run Test Cases to Verify and Debug Code**

The function is `compareVersions(version1, version2)`.

## Examples

The problem demonstrates the comparison rules with examples instead of stating them:

```text
0.1 < 1 = 1.0 < 1.1.3 < 1.1.4 < 1.2 = 1.2.0.0 < 1.18.2 < 13.37
```

## Step 1: Understand the Problem and Requirements

### Input and Output

```text
- Input: two version numbers in string representation, version1 and version2
- Output: one of the numbers from 1, 0, and -1; or null for invalid inputs
```

### Definitions and Rules

The rules for comparing version numbers are not clearly laid out. They are only demonstrated with examples, so we must examine the examples to infer the rules. A first pass:

```text
- if any inputs contain invalid characters, return null
  - any characters other than digits and . are considered invalid
  - a version number that begins or ends with a period or has more than one period in a row, is invalid.
- Compare the two input versions
  - if version1 > version2, return 1
  - if version1 < version2, return -1
  - if version1 === version2, return 0
```

This works at a high level, but we must break down further **exactly how to compare two valid version numbers**.

This step is crucial and may be the most challenging part of the problem. Without a strong mental model of the requirements, there's no clarity about the algorithm. Without a clear algorithm, there's no direction for the code. Jumping straight to coding means working on all three levels (requirements, algorithm, and programming) at the same time.

A useful question: **How would you explain the rules for comparing two version numbers to a non-technical person?** Non-technical language keeps the focus on interpreting the requirements, not on a solution.

### Work Through an Example by Hand

Compare `2.3.4` and `2.3.5`, starting with the first number part of each:

```text
v
2.3.4
2.3.5
^
```

- If the first version's number is larger, the first version is larger.
- If the second version's number is larger, the first version is smaller.
- Here the numbers are the same, so move on to the next number part.

The next part is also the same, so continue:

```text
  v
2.3.4
2.3.5
| ^
|
same
```

The third parts differ. 4 is smaller than 5, so the first version number is smaller:

```text
    v
2.3.4
2.3.5
| | ^
| |
| same
same
```

### Requirements After Step 1

Verbalize the hand-worked example and combine it with the first pass:

```text
- if any inputs contain invalid characters, return null
  - any characters other than digits and . are considered invalid
- Compare the two input versions
  - if version1 > version2, return 1
  - if version1 < version2, return -1
  - if version1 === version2, return 0
- The rules to compare two version numbers
  - start from the left most parts of the two version numbers
  - if the number part of the first version number is larger, then the first version number is larger
  - if the number part of the second version number is larger, then the first version number is smaller
  - if the number parts of both version numbers are the same, move to the next number part of the two version numbers
    - do the same comparison and decide which version number is larger
    - keep moving to the right until the result of the comparison is determined
    - if we get to the last number part of the two version numbers and they're equal,
      then the two version numbers are equal
```

## Step 2: Create Examples / Test Cases

### Generic Cases

```text
1 is equal to 1
1.1 is greater than 1.0
2.3.4 is less than 2.3.5
```

### Edge Cases

```text
1.a is not a valid version          // we only want to deal with numbers and dots
.1 and 1. are not valid versions    // versions must begin and end with a number
1..0 is not a valid version         // dots can only appear between two numbers
1.0 and 1.0.0 are equal to 1        // zeros can be inferred but are not always shown
1.0.0 is less than 1.1              // can handle version numbers with different lengths
1.0 is less than 1.0.5              // can handle version numbers with different lengths
```

These test cases carry us through the rest of the steps, as a guide and as concrete examples for verifying our work.

### Formal Test Cases

```javascript
console.log(compareVersions('1', '1'));            // 0
console.log(compareVersions('1.1', '1.0'));        // 1
console.log(compareVersions('2.3.4', '2.3.5'));    // -1
console.log(compareVersions('1.a', '1'));          // null
console.log(compareVersions('.1', '1'));           // null
console.log(compareVersions('1.', '2'));           // null
console.log(compareVersions('1..0', '2.0'));       // null
console.log(compareVersions('1.0', '1.0.0'));      // 0
console.log(compareVersions('1.0.0', '1.1'));      // -1
console.log(compareVersions('1.0', '1.0.5'));      // -1
```

### Use Test Cases to Generalize the Requirements

The Step 1 requirements came from a single example (2.3.4 < 2.3.5), so they are **too specific**. They don't say how to handle these test cases:

```javascript
compareVersions('1.0', '1.0.0');    // 0
compareVersions('1.0.0', '1.1');    // -1
compareVersions('1.0', '1.0.5');    // -1
```

The test cases give a more complete view, so we must generalize the requirements to include **version numbers with different lengths**.

**Key insight:** trailing zero parts don't change a version number's value. So we can **pad** a version number with zeros when we reach its end. After comparing the 0 parts in 1.0 and 1.0.5, pad 1.0 to 1.0.0 and compare it with 1.0.5. The first version is smaller.

### Updated Requirements

```text
- if any inputs contain invalid characters, return null
  - any characters other than digits and . are considered invalid
- Compare the two input versions
  - if version1 > version2, return 1
  - if version1 < version2, return -1
  - if version1 === version2, return 0
- The rules to compare two version numbers
  - start from the left most parts of the two version numbers
  - if the number part of the first version number is larger, then the first version number is larger
  - if the number part of the second version number is larger, then the first version number is smaller
  - if the number parts of both version numbers are the same, move to the next number part of the two version numbers
    - do the same comparison and decide which version number is larger
    - keep moving to the right until the result of the comparison is determined
      - if we reach the end of only one number, pad that number with a 0 part
    - if we get to the last number part of the two version numbers and they're equal,
      then the two version numbers are equal
```

## Step 3: Data Structure and Algorithm

### Data Structure Choices

The primary concern: **how do we represent the data so we can best use JavaScript's built-in methods?**

The requirements show two key operations:

```text
- iterate through the version numbers, part by part
- compare part numbers
```

An **array of numbers** makes both operations easy to express.

### Algorithm

The goal is to:

```text
- convert the input data into our data structure of choice
- express steps to produce outputs, using methods and abstractions available on the data structure
```

The algorithm:

```text
- return null if the inputs contain any characters other than digits and dots
- split the input numbers into parts as arrays of integers
- loop through the two version numbers' parts
  - for each step, access one part from each version number
  - if one version number runs out of parts, use 0
  - compare the two parts
    - if part1 < part2
      - return -1
    - if part1 > part2
      - return 1
    - if part1 === part2
      - we move to the next pair of parts
- when we reach the end of the loop, return 0
```

This is a close translation of the requirements, but in language much closer to JavaScript, so it is easy to translate to code.

**Before coding, go over your test cases by hand** to verify the algorithm works with all of them. Fixing the algorithm ahead of time lowers the risk of wasting time on buggy code. This is especially important in interviews.

## Step 4: Translate Algorithm Steps Into Code

With all the work so far, writing the code is easy:

```javascript
function compareVersions(versionA, versionB) {
  let validChars = /^[0-9]+(\.[0-9]+)*$/;

  if (!validChars.test(versionA) || !validChars.test(versionB)) {
    return null;
  }

  let aParts = versionA.split('.').map(Number);
  let bParts = versionB.split('.').map(Number);

  for (let i = 0; i < aParts.length; i += 1) {
    let aValue = aParts[i] || 0;
    let bValue = bParts[i] || 0;

    if (aValue > bValue) {
      return 1;
    } else if (aValue < bValue) {
      return -1;
    }
  }

  return 0;
}
```

## Step 5: Run Test Cases to Verify and Debug Code

```javascript
console.log(compareVersions('1', '1'));            // 0
console.log(compareVersions('1.1', '1.0'));        // 1
console.log(compareVersions('2.3.4', '2.3.5'));    // -1
console.log(compareVersions('1.a', '1'));          // null
console.log(compareVersions('.1', '1'));           // null
console.log(compareVersions('1.', '2'));           // null
console.log(compareVersions('1..0', '2.0'));       // null
console.log(compareVersions('1.0', '1.0.0'));      // 0
console.log(compareVersions('1.0.0', '1.1'));      // -1
console.log(compareVersions('1.0', '1.0.5'));      // -1 (this doesn't work yet)
```

All test cases pass except the last one. Revisit the code to find out why, and think about **how these inputs differ from the inputs in the passing test cases**.

```javascript
function compareVersions(versionA, versionB) {
  // ...

  for (i = 0; i < aParts.length; i += 1) {

    // ...
```

The `for` loop uses the number of parts in the **first** version to decide how many times to loop. When comparing 1.0 to 1.0.5, the second version is longer. The code compares the first two parts, finds them equal, and exits the loop without ever checking the third part (5). That's why it wrongly returns 0.

**The fix:** loop once for each part in the **longest** version number:

```javascript
function compareVersions(versionA, versionB) {

  // ...

  let maxLength = Math.max(aParts.length, bParts.length);

  // ...

  for (i = 0; i < maxLength; i += 1) {

    // ...
```

### Final Code

Now the code passes all the test cases:

```javascript
function compareVersions(versionA, versionB) {
  let validChars = /^[0-9]+(\.[0-9]+)*$/;

  if (!validChars.test(versionA) || !validChars.test(versionB)) {
    return null;
  }

  let aParts = versionA.split('.').map(Number);
  let bParts = versionB.split('.').map(Number);
  let maxLength = Math.max(aParts.length, bParts.length);

  for (let i = 0; i < maxLength; i += 1) {
    let aValue = aParts[i] || 0;
    let bValue = bParts[i] || 0;

    if (aValue > bValue) {
      return 1;
    } else if (aValue < bValue) {
      return -1;
    }
  }

  return 0;
}
```

## Edge Cases

- **Invalid characters:** `'1.a'` returns `null`. Only digits and dots are allowed.
- **Leading or trailing dots:** `'.1'` and `'1.'` return `null`. Versions must begin and end with a number.
- **Consecutive dots:** `'1..0'` returns `null`. Dots can only appear between two numbers.
- **Inferred zeros:** `'1.0'` and `'1.0.0'` are equal to `'1'`. Trailing zero parts don't change the value.
- **Different lengths:** `'1.0'` vs. `'1.0.5'` returns `-1`. The shorter version is padded with 0 parts.

## Common Mistakes

- **Skipping the requirements step** and jumping to the algorithm or code, which means working on requirements, algorithm, and code all at once.
- **Deriving rules from a single example.** The Step 1 rules came from 2.3.4 vs. 2.3.5 only and missed versions of different lengths. Test cases exposed the gap.
- **Looping over only the first input's length.** Using `aParts.length` skips the extra parts of a longer second version, so `compareVersions('1.0', '1.0.5')` wrongly returns 0. Loop to `Math.max(aParts.length, bParts.length)`.
- **Not checking the algorithm by hand** against the test cases before writing code.
