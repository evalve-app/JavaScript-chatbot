# PEDAC Guided Practice: Sort by Most Adjacent Consonants

## Explanation

This lesson solves a small programming problem step by step using the PEDAC process. It also covers **how to debug a solution that runs but fails some test cases**.

For each step, **do the task before reading the discussion**, and finish one step before moving on. Your notes, algorithm, and solution don't need to match the Launch School version. They should reflect how **you** approached each step. If you missed something in your initial exploration, think about why, and use that to improve your process.

## Examples

### The Problem: Sort Strings by Most Adjacent Consonants

Given an array of strings, return a new array where the strings are sorted to the highest number of adjacent consonants a particular string contains. If two strings contain the same highest number of adjacent consonants they should retain their original order in relation to each other. Consonants are considered adjacent if they are next to each other in the same word or if there is a space between two consonants in adjacent words.

Note that for this problem, the letters 'y' and 'w' should be treated as consonants.

### Test Cases

```javascript
let list1 = ['aa', 'baa', 'ccaa', 'dddaa'];
console.log(sortStringsByConsonants(list1));
// ['dddaa', 'ccaa', 'aa', 'baa']

let list2 = ['can can', 'toucan', 'batman', 'salt pan'];
console.log(sortStringsByConsonants(list2));
// ['salt pan', 'can can', 'batman', 'toucan']

let list3 = ['bar', 'car', 'far', 'jar'];
console.log(sortStringsByConsonants(list3));
// ['bar', 'car', 'far', 'jar']

let list4 = ['day', 'week', 'month', 'year'];
console.log(sortStringsByConsonants(list4));
// ['month', 'day', 'week', 'year']
```

## Step 1: Understand the Problem

**Tasks:**

- Make notes of your mental model for the problem, including explicit and implicit rules.
- Write a list of questions for anything that isn't clear from the description.

### Input / Output

```text
- Input: array of strings
- Output: an array of strings sorted according to the
          highest number of adjacent consonants
```

### Explicit Rules

- If two strings contain the same count of adjacent consonants, they should **maintain their original relative order**.
- The letters **'y' and 'w' are consonants**.
- Adjacent consonants are:
  - Next to each other in the same string
  - Can have a space between them in adjacent words

The second rule about adjacent consonants isn't entirely clear, so it goes on the questions list.

### Implicit Rules

There aren't many obvious implicit rules. Perhaps the only one comes from the mention of words:

- Strings can contain multiple words

### Questions

Several things are unclear and could become implicit rules with more information. Many relate to **what the strings contain**. There's also the unclear rule about spaces between consonants, and the **direction of the sort**. When working with strings, you often need to clarify **whether uppercase and lowercase letters are treated as equivalent**.

- Do strings always contain multiple words?
- Can strings contain a single word?
- Can strings be empty?
- Is it possible for a string to contain no adjacent consonants?
- What is meant by "a space between two consonants in adjacent words"?
- Should the strings be sorted in ascending or descending order?
- Is case important?

Some or all of these may be answered by the test cases.

## Step 2: Examples and Test Cases

**Task:** With your mental model and questions from Step 1, make notes on the test cases. Do they confirm or refute parts of your analysis? Do they answer your questions or raise new ones?

**Do strings always contain multiple words? Can they contain a single word?**
Most strings in the test cases are single words, but some are multiple words separated by spaces.

**Can strings be empty?**
The test cases don't answer this. In an interview, ask the interviewer. For this exercise, base the judgment on the test cases and **assume strings cannot be empty**.

**What is meant by "a space between two consonants in adjacent words"?**
`'can can'` and `'salt pan'` in the second test case answer this. The `n` at the end of the first `can` and the `c` at the start of the second count as adjacent. The `lt` at the end of `salt` and the `p` at the start of `pan` also count as adjacent. So:

- `'salt pan'`: 3 adjacent consonants
- `'can can'` and `'batman'`: 2 each
- `'toucan'`: none

The order in the expected output confirms this.

**Ascending or descending order?**
The first, second, and last test cases show **descending order**: the string with the most adjacent consonants comes first. The third test case has no strings with adjacent consonants, so its order is unchanged.

**Is case important?**
All strings in the test cases are lowercase, so case doesn't matter here. In an interview, you may still want to clarify it.

### New Detail Surfaced by the Test Cases

Test cases can surface details that weren't in your initial analysis or questions. In the first test case, `'aa'` comes before `'baa'`, even though `'aa'` has no consonants and `'baa'` has one. That matches their original input order, so **a single consonant doesn't affect the sort order. Only adjacent consonants do.** Add it to the implicit rules:

- Single consonants in a string do not affect sort order in comparison to strings with no consonants. Only adjacent consonants affect sort order.

## Step 3: Data Structures

**Task:** Use your analysis so far to note whether you might need any particular data structures, and which ones.

The input and output are both **arrays**, so at a minimum we work with arrays.

We might need an intermediate structure, such as an **object** that tracks the number of adjacent consonants in each word:

```javascript
{
  'aa': 0,
  'baa': 0,
  'ccaa': 2,
  'dddaa': 3
}
```

This may be more of an implementation detail than a key part of the mental model at this stage. You can always return to the Data Structures step later.

## Step 4: Algorithm

**Task:** Write a high-level algorithm that solves the problem at an abstract level. Avoid too much implementation detail.

### High-Level Algorithm

```text
- For each string in the input array, determine the
  highest number of adjacent consonants within that string

- Sort the input array based on the calculated highest
  number of consonants from step 1

- Return the sorted array
```

This outline needs more detail before implementation, but it shows **where to focus your effort**:

- **Returning the sorted array is trivial.**
- **Sorting:** if you've solved sorting problems before, you probably know `Array.prototype.sort` can do this. You don't want to think too far ahead to implementation, but familiarity with types of problems helps when abstracting parts of the algorithm.
- **The first step needs the most thought.**

### Sub-Algorithm: Count the Most Adjacent Consonants

The first step is a **repeatable action performed on each string**, which suggests a helper function. Either way, it makes sense to write a specific algorithm just for this step.

When defining a **sub-algorithm** inside a larger algorithm, be clear on its requirements and **treat it as a separate problem**:

> Given a string, return a count of the highest number of adjacent consonants anywhere in that string.

- **Input:** a string
- **Output:** an integer representing a count of the highest number of adjacent consonants in the string

The rules and mental model come from the overall problem, but it helps to write specific test cases for the sub-problem:

```javascript
console.log(countMaxAdjacentConsonants('dddaa')); // 3
console.log(countMaxAdjacentConsonants('ccaa'));  // 2
console.log(countMaxAdjacentConsonants('baa'));   // 0
console.log(countMaxAdjacentConsonants('aa'));    // 0
```

The idea: go through the string **letter by letter**.

- If the letter is a vowel, continue to the next letter.
- If the letter is a consonant, store it in a temporary string. Keep adding consonants while they continue.
- When you hit a vowel, count the length of the temporary string and update a count.

Two more things from the earlier analysis:

- Remove any spaces from the input string.
- Don't update the count if the temporary string has only a single consonant.

```text
- Remove the spaces from the input string
- Initialize a count to zero
- Initialize a temporary string to an empty string
- Iterate through the input string. For each letter:
    - If the letter is a consonant:
        - concatenate it to the temporary string
    - If the letter is a vowel:
        - If the temporary string has a length greater than 1
          AND the temporary string length is greater than the
          current count:
            - set the count to the length of the temporary
              string
        - Reset the temporary string to an empty string
- Return the count
```

This is probably enough to implement the sub-problem. You can always return to the algorithm step to add more detail.

## Step 5: Implement a Solution in Code

**Task:** Implement a working solution in JavaScript that passes all the test cases.

### Implement and Test the Helper First

Implement `countMaxAdjacentConsonants` as a helper function and **test it in isolation** first. Implementation notes:

- Use `String.prototype.split` with `Array.prototype.join` to remove the spaces from the input string
- Maybe use a `for` loop to iterate through the string?
- Use `String.prototype.includes` to check whether a string of consonants includes the letter for that iteration

As you implement, you may want to test these methods in isolation to make sure they do what you expect.

```javascript
function countMaxAdjacentConsonants(string) {
  string = string.split(' ').join('');

  let count = 0;
  let tempStr = '';

  for (let i = 0; i < string.length; i++) {
    let letter = string[i];

    if ('bcdfghjklmnpqrstvwxyz'.includes(letter)) {
      tempStr += letter;
    } else {
      if (tempStr.length > 1 && tempStr.length > count) {
        count = tempStr.length;
      }

      tempStr = '';
    }
  }

  return count;
}
```

This closely matches the sub-algorithm. Run its test cases:

```javascript
console.log(countMaxAdjacentConsonants('dddaa')); // 3
console.log(countMaxAdjacentConsonants('ccaa'));  // 2
console.log(countMaxAdjacentConsonants('baa'));   // 0
console.log(countMaxAdjacentConsonants('aa'));    // 0
```

They all pass.

### Implement the Main Function

If you're familiar with `Array.prototype.sort`, the main function isn't complicated. One implementation note:

- Ensure correct order of arguments in the callback to `sort` to produce a descending order

```javascript
function sortStringsByConsonants(strings) {
  let stringsCopy = strings.slice();

  let sortedStrings = stringsCopy.sort((a, b) => {
    return countMaxAdjacentConsonants(b) -
           countMaxAdjacentConsonants(a);
  });

  return sortedStrings;
}

function countMaxAdjacentConsonants(string) {
  string = string.split(' ').join('');

  let count = 0;
  let tempStr = '';

  for (let i = 0; i < string.length; i++) {
    let letter = string[i];

    if ('bcdfghjklmnpqrstvwxyz'.includes(letter)) {
      tempStr += letter;
    } else {
      if (tempStr.length > 1 && tempStr.length > count) {
        count = tempStr.length;
      }

      tempStr = '';
    }
  }

  return count;
}
```

### Run the Main Test Cases

All pass except the last one:

```javascript
let list1 = ['aa', 'baa', 'ccaa', 'dddaa'];
console.log(sortStringsByConsonants(list1));
// Expected: ['dddaa', 'ccaa', 'aa', 'baa']
// Actual:   ['dddaa', 'ccaa', 'aa', 'baa']

let list2 = ['can can', 'toucan', 'batman', 'salt pan'];
console.log(sortStringsByConsonants(list2));
// Expected: ['salt pan', 'can can', 'batman', 'toucan']
// Actual:   ['salt pan', 'can can', 'batman', 'toucan']

let list3 = ['bar', 'car', 'far', 'jar'];
console.log(sortStringsByConsonants(list3));
// Expected: ['bar', 'car', 'far', 'jar']
// Actual:   ['bar', 'car', 'far', 'jar']

let list4 = ['day', 'week', 'month', 'year'];
console.log(sortStringsByConsonants(list4));
// Expected: ['month', 'day', 'week', 'year']
// Actual:   ['day', 'week', 'month', 'year']
```

## Debugging: Syntax Errors vs. Logic Errors

When you hit a bug, first understand **what type of bug** it is. That tells you what level to think at to fix it.

### Syntax Errors (Implementation Errors)

- The code **won't run**, and you get useful error output, often with a specific line number to start from.
- The source of the bug is **the code you wrote**, not the solution itself.
- Be methodical and use the error message. You can usually resolve these **at the code level**.

### Logic Errors

- The code **runs**, and some but not all test cases pass, like the solution above.
- The underlying source is usually **your algorithm and/or mental model**, not the code itself.
- You may start at the code level (to isolate the bug, or to spot a mismatch between code and algorithm), but ultimately you need to **zoom back out and revisit the algorithm**.

### Avoid Hack and Slash Debugging

You need **clarity about the cause** of the bug. Avoid changing pieces of the implementation by guesswork without a clear plan.

Here it would be easy to assume the problem is in the `sort` callback, since `countMaxAdjacentConsonants` passed its tests in isolation. Assumptions like that, without analysis, lead down the hack and slash path and could make you **fixate on the wrong part of the code**.

### Isolate the Bug

The first step is to **isolate the source of the bug**. This is partly at the code level, but you also need to switch up to the algorithm and mental model.

- **Log output.** Logging is a big part of isolating a bug.
- **Focus on a single test case.** Comment out the others to cut out "noise" from the logging. The failing test case is the obvious candidate.

The failing test case should return:

```javascript
// ['month', 'day', 'week', 'year']
```

but returns:

```javascript
// ['day', 'week', 'month', 'year']
```

The order hasn't changed. None of the strings has adjacent consonants **except `'month'`, which has three: `nth`**. For some reason the solution doesn't count `nth`. Start there: call `countMaxAdjacentConsonants` with `'month'` and log the key values, `tempStr` and `count`:

```javascript
function countMaxAdjacentConsonants(string) {
  string = string.split(' ').join('');

  let count = 0;
  let tempStr = '';

  for (let i = 0; i < string.length; i++) {
    let letter = string[i];

    if ('bcdfghjklmnpqrstvwxyz'.includes(letter)) {
      tempStr += letter;
    } else {
      if (tempStr.length > 1 && tempStr.length > count) {
        count = tempStr.length;
      }

      tempStr = '';
    }

    console.log({tempStr}, {count});
  }

  return count;
}

countMaxAdjacentConsonants('month');
```

Logged output:

```javascript
// { tempStr: 'm' } { count: 0 }
// { tempStr: '' } { count: 0 }
// { tempStr: 'n' } { count: 0 }
// { tempStr: 'nt' } { count: 0 }
// { tempStr: 'nth' } { count: 0 }
```

The count should end at 3, but it's 0.

### Find the Cause in the Algorithm

Revisiting the algorithm explains it: **the count is only updated when we hit a vowel**. That works when consonants are followed by a vowel, but **not when the consonants are at the end of the string**.

The code mirrors the algorithm: `count = tempStr.length` is only set in the `else` branch. The fix is to update the count **right after concatenating a consonant**:

```javascript
function sortStringsByConsonants(strings) {
  let stringsCopy = strings.slice();

  let sortedStrings = stringsCopy.sort((a, b) => {
    return countMaxAdjacentConsonants(b) -
           countMaxAdjacentConsonants(a);
  });

  return sortedStrings;
}

function countMaxAdjacentConsonants(string) {
  string = string.split(' ').join('');
  let count = 0;
  let tempStr = '';
  for (let i = 0; i < string.length; i++) {
    let letter = string[i];

    if ('bcdfghjklmnpqrstvwxyz'.includes(letter)) {
      tempStr += letter;

      if (tempStr.length > 1 && tempStr.length > count) {
        count = tempStr.length;
      }
    } else {
      tempStr = '';
    }
  }

  return count;
}
```

Be careful to place the nested conditional **after the concatenation**. Now all the test cases pass:

```javascript
let list1 = ['aa', 'baa', 'ccaa', 'dddaa'];
console.log(sortStringsByConsonants(list1));
// ['dddaa', 'ccaa', 'aa', 'baa']

let list2 = ['can can', 'toucan', 'batman', 'salt pan'];
console.log(sortStringsByConsonants(list2));
// ['salt pan', 'can can', 'batman', 'toucan']

let list3 = ['bar', 'car', 'far', 'jar'];
console.log(sortStringsByConsonants(list3));
// ['bar', 'car', 'far', 'jar']

let list4 = ['day', 'week', 'month', 'year'];
console.log(sortStringsByConsonants(list4));
// ['month', 'day', 'week', 'year']
```

## Edge Cases

- **Consonants at the end of a string:** `'month'` ends in `nth`. The first implementation only updated the count at a vowel, so it returned 0 instead of 3.
- **Consonants across a space:** `'salt pan'` has 3 adjacent consonants (`ltp`) and `'can can'` has 2 (`nc`). Spaces are removed before counting.
- **Single consonants:** `'baa'` counts as 0, the same as `'aa'`. Only runs of 2 or more consonants count.
- **Ties keep their original order:** in `list3`, no string has adjacent consonants, so the order is unchanged. In `list1`, `'aa'` stays before `'baa'`.
- **'y' and 'w' are consonants:** they're included in the consonant string `'bcdfghjklmnpqrstvwxyz'`.
- **Empty strings and uppercase letters:** not covered by the test cases. The solution assumes non-empty, lowercase strings. In an interview, ask.

## Common Mistakes

- **Forgetting the sort direction.** The callback must return `b - a` (using the counts) to sort in descending order.
- **Mutating the input.** The problem asks for a new array, so copy it with `slice()` before calling `sort`, which sorts in place.
- **Only updating the count when a vowel appears**, which misses consonant runs at the end of a string.
- **Assuming a passing helper means the bug is elsewhere.** `countMaxAdjacentConsonants` passed its own tests but still had the bug. Its sub-problem test cases didn't include a string ending in consonants.
- **Hack and slash debugging.** Changing code by guesswork instead of isolating the bug with logging and a single failing test case.
- **Staying at the code level for logic errors.** Logic errors usually come from the algorithm or mental model, so zoom back out.
