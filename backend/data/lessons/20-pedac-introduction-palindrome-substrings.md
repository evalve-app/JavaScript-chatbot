# Introduction to the PEDAC Process: Palindrome Substrings

## Explanation

The **PEDAC** process is one approach to solving programming problems. Its primary goal is to help you **identify and avoid pitfalls** you may encounter when you don't code with intent.

- **P** – [Understand the] Problem
- **E** – Examples / Test cases
- **D** – Data Structure
- **A** – Algorithm
- **C** – Code

This guide describes a **"lighter" version** of PEDAC to help prepare for the interview assessment.

### Why not jump straight to code?

Students often jump straight to coding. In an interview with limited time, writing an algorithm can seem like a waste, especially when the problem seems simple. But following PEDAC **saves time** and lets you solve **complex** problems efficiently.

- **Simple problems** don't need a detailed algorithm. Example: a function that takes a string and returns its uppercased version.
- **Complex problems** do. Example: a function that returns all the substrings of a string that are palindromes. Following PEDAC is crucial to solving it in the time allotted.

### Focus of this guide

This guide focuses on **"understand the problem"** and **"data structure/algorithm"**:

- **Examples/Test Cases** get little attention, because test cases are provided during the JS119 interview assessment.
- **Code** gets little attention, because most students know enough JavaScript syntax, functions, and methods to solve even the hardest problems. Where they run into trouble is **understanding the problem and determining an appropriate algorithm**.

## P – Understand the Problem

Understanding the problem has three steps:

1. **Read the problem description.**
2. **Check the test cases**, if any.
3. **Ask the interviewer or problem requester** to clarify anything that is unclear.

### Example: `changeMe`

```javascript
// PROBLEM:

// Given a string, write a function changeMe which returns the same
// string but with all the words in it that are palindromes uppercased.

// changeMe("We will meet at noon") === "We will meet at NOON"
// changeMe("No palindromes here") === "No palindromes here"
// changeMe("") === ""
// changeMe("I LOVE my mom and dad equally") === "I LOVE my MOM and DAD equally"
```

### Items That May Need Clarification

- **What is a palindrome?** Ask the interviewer. They would say it is a word that reads the same forwards and backward.
- **Should words that already use uppercase stay the same?** Check the test cases. In the fourth test case, `LOVE` is already uppercase and stays uppercase.
- **How should I handle empty strings?** Test cases frequently answer this. Test case 3 does here. This is an **implicit requirement** inferred from the test cases.
- **Can I assume all inputs are strings?** The test cases don't show non-string inputs, so ask whether inputs can be non-strings and what to do with them. In this problem, we won't worry about non-string values.
- **Should letter case matter when deciding whether a word is a palindrome?** The test cases don't show this. The interviewer might say palindromes are **case sensitive**: `mom` is a palindrome, `Mom` is not.
- **Do I return the same object or an entirely new one?** Not relevant here, because JavaScript strings are immutable and any operation on them returns a new string. In general, though, this is **one of the most important and most overlooked questions**. Students often assume they should return the same object and start solving without checking. They can lose 10–15 minutes struggling with the wrong problem.

**Always verify your assumptions** by looking at the test cases or asking the interviewer. Assumptions that don't match what the interviewer has in mind waste time on an incorrect or incomplete solution. Confirm them before you start developing your algorithm.

### Write Down Inputs, Outputs, and Rules

To finish this step, write down the inputs and outputs, and describe the rules. The rules should capture **all explicit and implicit requirements**. Identify and write down the explicit requirements first, then the implicit ones:

```javascript
// input: string
// output: string (not the same object)
// rules:
//      Explicit requirements:
//        - every palindrome in the string must be converted to
//          uppercase. (Reminder: a palindrome is a word that reads
//          the same forwards and backward).
//        - Palindromes are case sensitive ("Dad" is not a palindrome, but
//          "dad" is.)

//      Implicit requirements:
//        - if the string is an empty string, the result should be an empty string
```

## Data Structure / Algorithm

Data structures influence the algorithm, so these two steps are often paired.

- **Choosing a data structure is generally easy.** A case that calls for an array rather than an object, for instance, is usually easy to identify.
- **Designing the right algorithm is far more challenging.** The biggest problem students have when writing algorithms is **providing sufficient detail**.

## Examples

### The `palindromeSubstrings` Problem

```javascript
// PROBLEM:

// Given a string, write a function `palindromeSubstrings` which returns
// all the substrings from a given string which are palindromes and 2 or more characters long.
// Consider palindrome words case sensitive.

// Test cases:

// console.log(palindromeSubstrings("supercalifragilisticexpialidocious"))
// should return: ["ili"]
//
// console.log(palindromeSubstrings("abcddcbA"))
// should return: ["bcddcb", "cddc", "dd"]
//
// console.log(palindromeSubstrings("palindrome"))
// should log: []
//
// console.log(palindromeSubstrings(""))
// should log: []
```

### A High-Level Algorithm

```javascript
// Algorithm:
//  - declare a result variable and initialize it to an empty array
//  - create an array named substrArray that contains all of the
//    substrings of the input string that are at least 2 characters long.
//  - loop through the words in the substrArray array.
//  - if the word is a palindrome, append it to the result
//    array
//  - return the result array
```

**Does this algorithm look complete?** It is a "high-level" algorithm, like those students often write in interviews. It looks complete, but ask: **what is the hardest part of this problem?**

- Determining whether a word is a palindrome isn't that difficult for most students.
- Looping through the array and selecting the palindromes is relatively easy.
- **Finding all the substrings of a string is the challenging part**, and the algorithm doesn't tackle it. It **lacks implementation details for the "hard" parts**.

A student who starts coding from this algorithm soon realizes that returning all the substrings won't be easy. Ideally, they would return to the algorithm, work out how to find all the substrings, and maybe create a new function named `substrings`. In practice, time pressure often pushes them into a **hack and slash** approach instead. That almost always means spending more time than necessary, or not solving the problem at all.

### The Correct Approach: Code the High-Level Algorithm, Then Fill In Helpers

First, write code for the high-level algorithm:

```javascript
function palindromeSubstrings(str) {
  let result = [];
  let substringsArr = substrings(str);

  substringsArr.forEach(substring => {
    if (isPalindrome(substring)) {
      result.push(substring);
    }
  });

  return result;
}
```

This calls `substrings` and `isPalindrome`, which aren't defined yet. Instead of trying to code them right away, **return to the algorithm** and work out how they need to work, starting with `substrings`.

### Working Out the `substrings` Algorithm

**Simplify the problem with a small, concrete example.** Take the word `halo` and list all its substrings of at least 2 characters:

```text
['ha', 'hal', 'halo', 'al', 'alo', 'lo']
```

There's a pattern, and it involves nested looping:

- **The outer loop iterates over the starting index.** For `halo`, iterate over `h`, `a`, and `l`. Skip `o`, since no substring of at least 2 characters starts there.
- **The inner loop iterates over substring lengths** for that starting index: length 2, then 3, and so on.

```text
for each starting index from 0 through the next to last index position
  for each substring length from 2 until there are no substrings of that length
    extract the substring of the indicated length starting at the indicated index position
  end of inner loop
end of outer loop
```

Walking through `halo`:

- **Index 0 (`h`)**: lengths 2 to 4 → `'ha'`, `'hal'`, `'halo'`
- **Index 1 (`a`)**: lengths 2 to 3 → `'al'`, `'alo'`
- **Index 2 (`l`)**: length 2 only, one iteration → `'lo'`

For a 7-character string such as `goalies`, the outer loop goes from index 0 (`g`) to index 5 (`e`), and the inner loop's length range shrinks each time:

| Outer iteration | Substring lengths |
|---|---|
| 1st | 2 to 7 |
| 2nd | 2 to 6 |
| 3rd | 2 to 5 |
| 4th | 2 to 4 |
| 5th | 2 to 3 |
| 6th | 2 only |

From these two examples:

- The **outer loop** iterates over indices from 0 to the next-to-last index position: `string.length - 2`.
- The **inner loop** ranges from 2 to `string.length - startingIndex`.

### Complete Algorithm for `substrings`

```javascript
// - create an empty array called `result` that will contain all required substrings
// - create a `startingIndex` variable (value `0`) for the starting index of a substring
// - start a loop that uses `startingIndex` to iterate over `string` from `0` to the length of the string minus 2
//   - create a `numChars` variable (value `2`) for the length of a substring
//   - start an inner loop that uses `numChars` to iterate over `string` from `2` to `string.length - startingIndex`
//     - extract a substring of length `numChars` from `string` starting at `startingIndex`
//     - append the extracted substring to the `result` array
//     - increment the `numChars` variable by `1`
//   - end the inner loop
//   - increment the `startingIndex` variable by `1`
// - end the outer loop
// - return the `result` array
```

### Optional: Formal Pseudocode

Because this pseudocode is relatively complex, you might convert it to **formal pseudocode**:

```text
START

  /* Given a string named `string` */

  SET result = []
  SET startingIndex = 0

  WHILE startingIndex <= length of string - 2
    SET numChars = 2
    WHILE numChars <= length of string - startingIndex
      SET substring = numChars characters from string starting at index startingIndex
      append substring to result array
      SET numChars = numChars + 1

    SET startingIndex = startingIndex + 1

  RETURN result

END
```

Formal pseudocode is an **intermediate step** between informal pseudocode and program code. It isn't always needed, but it can sometimes help.

### Code for `substrings`

```javascript
function substrings(str) {
  let result = [];
  let startingIndex = 0;

  while (startingIndex <= str.length - 2) {
    let numChars = 2;
    while (numChars <= str.length - startingIndex) {
      let substring = str.slice(startingIndex, startingIndex + numChars);
      result.push(substring);
      numChars += 1;
    }

    startingIndex += 1;
  }

  return result;
}
```

It is very similar to the formal pseudocode, which made writing it straightforward. You could write the same code from the informal pseudocode, too.

### `isPalindrome`

Checking for a palindrome is easy, but a separate function makes the code more readable:

```javascript
// - Inside the `isPalindrome` function, check whether the string
//   value is equal to its reversed value.
```

Use `Array.prototype.reverse` along with `split` and `join`:

```javascript
function isPalindrome(str) {
  return str === str.split('').reverse().join('');
}
```

### Complete Informal Pseudocode

```javascript
// input: a string
// output: an array of substrings
// rules: palindrome words should be case sensitive, meaning "abBA"
//        is not a palindrome

// Algorithm:
//  substrings function
//  =================
//    - create an empty array called `result` that will contain all required substrings
//    - create a `startingIndex` variable (value `0`) for the starting index of a substring
//    - start a loop that uses `startingIndex` to iterate over `string` from `0` to the length of the string minus 2
//      - create a `numChars` variable (value `2`) for the length of a substring
//      - start an inner loop that uses `numChars` to iterate over `string` from `2` to `string.length - startingIndex`
//        - extract a substring of length `numChars` from `string` starting at `startingIndex`
//        - append the extracted substring to the `result` array
//        - increment the `numChars` variable by `1`
//      - end the inner loop
//      - increment the `startingIndex` variable by `1`
//    - end the outer loop
//    - return the `result` array

//  isPalindrome function
//  =====================
//    - Inside the `isPalindrome` function, check whether the string
//      value is equal to its reversed value.

//  palindromeSubstrings function
//  ============================
//    - declare a `result` variable and initialize it to an empty array
//    - create an array named `substrArray` that will contain all of the
//      substrings of the input string that are at least 2 characters long.
//    - loop through the words in the `substrArray` array.
//      - if the word is a palindrome, append it to the `result` array
//    - return the `result` array
```

### Complete Code With Helper Functions

```javascript
function substrings(str) {
  let result = [];
  let startingIndex = 0;

  while (startingIndex <= str.length - 2) {
    let numChars = 2;
    while (numChars <= str.length - startingIndex) {
      let substring = str.slice(startingIndex, startingIndex + numChars);
      result.push(substring);
      numChars += 1;
    }

    startingIndex += 1;
  }

  return result;
}

function isPalindrome(str) {
  return str === str.split('').reverse().join('');
}

function palindromeSubstrings(str) {
  let result = [];
  let substringsArr = substrings(str);

  substringsArr.forEach(substring => {
    if (isPalindrome(substring)) {
      result.push(substring);
    }
  });

  return result;
}

console.log(palindromeSubstrings("supercalifragilisticexpialidocious")); // ["ili"]
console.log(palindromeSubstrings("abcddcbA"));   // ["bcddcb", "cddc", "dd"]
console.log(palindromeSubstrings("palindrome")); // []
console.log(palindromeSubstrings(""));           // []
```

### Key Takeaways

- **You don't need to write all your pseudocode before you start coding.** Above, we wrote pseudocode for `palindromeSubstrings`, coded it, then returned to write pseudocode and code for the two lower-level functions.
- **You don't need the formal pseudocode step.** Use it if it helps, but it is an extra step.
- **You should be able to write a plain English solution to the problem.** If you can't, you won't be able to code it either.
- **You don't need any "fancy" functions** to solve these problems.

## Testing Frequently

Testing isn't properly part of PEDAC, but it's an important step you don't want to omit. **Test your code early and often while writing it.**

Starting the `substrings` function, you might write:

```javascript
function substrings(str) {
  let result = [];
  let startingIndex = 0;
  let numChars = 2;
  let endIndex = startingIndex + numChars;
}
```

Check that `endIndex` is correct with a `console.log` statement:

```javascript
function substrings(str) {
  let result = [];
  let startingIndex = 0;
  let numChars = 2;
  let endIndex = startingIndex + numChars;
  console.log(endIndex); // => 2
}

substrings("abcdef");
```

Add a bit more code and test again:

```javascript
function substrings(str) {
  let result = [];
  let startingIndex = 0;
  let numChars = 2;

  while (startingIndex <= str.length - 2) {
    startingIndex += 1;
  }

  console.log(startingIndex); // => 5
}

substrings("abcdef");
```

Continue this way. **Each time you write a bit of code you can test, test it** and confirm you get the answer you expect. Don't wait until you finish the whole program, function, or even an entire loop. The sooner you find a bug, the easier it is to identify what's wrong and fix it.

## Edge Cases

- **Empty string input:** `changeMe("")` returns `""`, and `palindromeSubstrings("")` returns `[]`. The test cases reveal this implicit requirement.
- **Already uppercase words:** In `changeMe`, `LOVE` stays uppercase.
- **Letter case in palindromes:** Palindromes are case sensitive. `"Dad"` and `"abBA"` are not palindromes. In `"abcddcbA"`, the full string is not a palindrome because of the uppercase `A`.
- **Non-string inputs:** Not shown by the test cases, so ask the interviewer.
- **Characters with no valid substrings:** The last character can't start a substring of 2 or more characters, so the outer loop stops at `string.length - 2`.

## Common Mistakes

- **Jumping straight to code** on complex problems.
- **Not verifying assumptions**, such as assuming you should return the same object. This can cost 10–15 minutes on the wrong problem.
- **Writing a high-level algorithm that skips the hard parts.** "Create an array of all substrings" looks complete but hides the most challenging step.
- **Falling into hack and slash coding** under time pressure instead of returning to the algorithm.
- **Writing a lot of code before testing any of it.**
