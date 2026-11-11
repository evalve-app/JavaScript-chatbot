# PEDAC: Understanding Problems and Writing Test Cases

## Explanation

This lesson answers common questions about the first two steps of the PEDAC process:

1. **Understanding the Problem**
2. **Examples / Test Cases**

It includes a full set of test cases for a hypothetical interview problem, `doubler`.

### How much effort should I put into "Understanding the Problem"? Can I skip it for obvious problems?

The bulk of this step is **translating the problem description into a specific, explicit set of definitions and rules**. How much effort you spend depends on:

- **The problem's complexity**
- **How the requirements are given.** Are they already in explicit "technical terms"? Or are they only demonstrated, expressed in higher "problem domain" terms, or full of implicit knowledge you must capture?

In larger projects, this is like a business analyst translating "business needs" into "technical requirements" for technical teams to implement.

### Where should I begin when breaking a problem down? I tend to think in terms of the solution.

1. **Capture the inputs and outputs** first.
2. Then focus on two aspects of the problem description:
   - **Definitions:** Are there key concepts that need to be more clearly defined?
   - **Rules:** Are there implied rules that need to be made explicit?

### What is a test case?

A **test case** is an example of how some code can be used. It usually combines the **input values** the program accepts with the **expected output** we want our code to produce.

There are two main types:

- **Generic cases** test the typical input values we expect our program to receive.
- **Edge cases** test less common input values that may require special handling. These can be invalid inputs we want to handle gracefully, or other specific scenarios we must consider.

## How to Come Up With Good Test Cases

### Input Types

Can the function take and handle different types of inputs, such as numbers, strings, booleans, and objects?

### Special Values

- **Numbers:** Does it work with zero, negative numbers, fractional numbers (e.g., `0.567`), or special values (e.g., `NaN`, `Infinity`)?
- **Strings, arrays, objects:** Does it work with an empty string, array, or object (`''`, `[]`, `{}`)?
- **Arrays:** Does it work with a **sparse array** (e.g., `[1, , 2]`) or an array with an object property (e.g., `[1, 2, a: "A"]`)?

### Valid / Invalid Inputs

- What counts as invalid input, and what should we do with it? If the input is supposed to be a "word", can we assume it's a string of only letters? Should we return a specific value, such as `null` or `undefined`, if it isn't a valid word? Does letter case matter? For example: `'a'`, `'dog'`, `'DOG'`, `'doG'`, `' dog'`, `'dog '`, `'dog cat'`, `'dogCat'`, `'dog_cat'`, `'@'`, `'dog4'`, `'4dog'`, `'42'`, `'dog\n'`.
- What should we do when an input is **omitted**? Issue an error message, return a specific value, or set a default and run the function normally?

### Cover the Requirements as Completely as Possible

- Cover **all** the requirements from your requirement breakdown, including generic cases and edge cases.
- **Look for the word "if"** in the requirements. Conditional requirements need test cases for **both sides of the condition**:

```javascript
// If one argument is a string and the other is a number,
// convert the second argument to the type of the first argument,
// then return both as a two-element array.
foo('42', 43);                               // ["42", "43"]
foo(42, '43');                               // [42, 43]
```

- **Avoid testing more than one requirement per test case.** Isolating each requirement makes it easier to validate and debug the solution later.
- It's fine to test **one requirement with several test cases**, especially complex ones like conditional requirements.

## Examples

### The `doubler` Problem

Problem description: **"Write a function called doubler that doubles every value in an array."** No test cases are given.

The description doesn't give much to work with, so we can't write good test cases without first **asking the interviewer for more information**. We ask a series of questions and translate the answers into requirements, then build test cases from those requirements.

This problem is hypothetical, but interview problems do sometimes have vague descriptions like this. The same skill matters whenever information is incomplete, such as when a business client gives a general outline of a project without specific details. Other problems come with an explicit description and a complete set of test cases, and then you may not need as many questions or your own test cases.

### Requirements From the Interviewer's Answers

```text
- elements that are numbers should be multiplied by 2
- elements that are strings should be repeated twice via concatenation
- other types of elements should be duplicated in the array
- the input array should not be mutated
- elements that are special number values should remain unchanged
- elements that are any other type of number should be treated normally (multiplied by 2)
- elements that are empty strings should remain unchanged
- elements that are any other type of string should be treated normally (repeated twice)
- the input array can contain a mixture of different types of elements
- non-primitive elements should have their reference duplicated, not their value
- elements that appear more than once should be treated normally (as specified above)
- elements that contain nested arrays or objects should be treated normally (duplicated)
- if the input array contains empty slots (a "sparse array"), they should be removed
- if an inner array (element) contains empty slots, they should remain unchanged
- if the input array contains any object properties, they should remain unchanged
- if an inner array (element) contains any object properties, they should remain unchanged
- if the array is empty, return an empty array
- if multiple arguments are passed, ignore all but the first
- if the argument is a string, treat it as an array of characters
- if the argument is a non-negative integer, treat it as an array of digits
- if the argument is an object, treat it as an array of its property values
- all other kinds of inputs are invalid, and should return the string 'Invalid input'
```

### Generic Cases

```javascript
// elements that are numbers should be multiplied by 2
doubler([1, 2, 3]);                    // [2, 4, 6]

// elements that are strings should be repeated twice via concatenation
doubler(['a', 'b', 'c']);              // ["aa", "bb", "cc"]

// other types of elements should be duplicated in the array
doubler([true, false]);                // [true, true, false, false]
doubler([null]);                       // [null, null]
doubler([undefined]);                  // [undefined, undefined]
doubler([[1], []]);                    // [[1], [1], [], []]
doubler([{ foo: 'bar' }]);             // [{ foo: "bar" }, { foo: "bar" }]
doubler([function foo() {}]);          // [function foo(), function foo()]
doubler([/abc/]);                      // [/abc/, /abc/]

// the input array should not be mutated
let array = [1, 2, 3];
doubler(array);                        // [2, 4, 6]
array;                                 // [1, 2, 3]
```

## Edge Cases

### `doubler` Edge Cases for Valid Inputs

```javascript
// elements that are special number values should remain unchanged
doubler([NaN, Infinity, -Infinity]);   // [NaN, Infinity, -Infinity]

// elements that are any other type of number should be treated normally (multiplied by 2)
doubler([0.42, -5, 0, -0]);            // [0.84, -10, 0, -0]

// elements that are empty strings should remain unchanged
doubler(['']);                         // [""]

// elements that are any other type of string should be treated normally (repeated twice)
doubler([' ', 'aB', '@', '\n', '1']);  // ["  ", "aBaB", "@@", "\n\n", "11"]

// the input array can contain a mixture of different types of elements
doubler([1, 'a', true, [], {}]);       // [2, "aa", true, true, [], [], {}, {}]

// non-primitive elements should have their reference duplicated, not their value
let doubled = doubler([{ a: 'b' }]);
doubled[0] === doubled[1];             // true

// elements that appear more than once should be treated normally (as specified above)
doubler([1, 1, true, true, {}, {}]);   // [2, 2, true, true, true, true, {}, {}, {}, {}]

// elements that contain nested arrays or objects should be treated normally (duplicated)
doubler([[1, [2, 3], {}]]);            // [[1, [2, 3], {}], [1, [2, 3], {}]]
doubler([{ a: [1] }]);                 // [{ a: [1] }, { a: [1] }]
```

```javascript
// if the input array contains empty slots (a "sparse array"), they should be removed
doubler([1, , 2, , , 3]);              // [2, 4, 6]

// if an inner array (element) contains empty slots, they should remain unchanged
doubler([[1, , , 2]]);                 // [[1, empty × 2, 2], [1, empty × 2, 2]]

// if the input array contains any object properties, they should remain unchanged
let array = [1, 2];
array.foo = 'bar';
doubler(array);                        // [2, 4, foo: "bar"]

// if an inner array (element) contains any object properties, they should remain unchanged
let array = [1, 2];
array.foo = 'bar';
doubler([array]);                      // [[1, 2, foo: "bar"], [1, 2, foo: "bar"]]

// if the input array is empty, return an empty array
doubler([]);                           // []

// if multiple arguments are passed, ignore all but the first
doubler(['a'], ['b']);                 // ['aa']
```

```javascript
// if the argument is a string, treat it as an array of characters
doubler('abc');                        // ["aa", "bb", "cc"]
doubler('123');                        // ["11", "22", "33"]
doubler('');                           // []

// if the argument is a non-negative integer, treat it as an array of digits
doubler(123);                          // [2, 4, 6]
doubler(0);                            // [0]

// if the argument is an object, treat it as an array of its property values
doubler({ a: 1, b: 2 });               // [2, 4]
doubler({ a: 'A', b: [] });            // ["AA", [], []]
doubler({});                           // []
```

### `doubler` Edge Cases for Invalid Inputs

```javascript
// all other kinds of inputs are invalid, and should return the string 'Invalid input'
doubler(-1);                           // "Invalid input"
doubler(0.42);                         // "Invalid input"
doubler(Infinity);                     // "Invalid input"
doubler(NaN);                          // "Invalid input"
doubler(true);                         // "Invalid input"
doubler(false);                        // "Invalid input"
doubler(null);                         // "Invalid input"
doubler(undefined);                    // "Invalid input"
doubler(function () {});               // "Invalid input"
doubler(/abc/);                        // "Invalid input"
doubler();                             // "Invalid input"
```

### Do I always need to consider every possible edge case?

Not always. If a function is part of a bigger program and the input is **guaranteed** to always be a string, you don't need test cases for other input types. But **whenever you're uncertain about some aspect of the input, cover the relevant edge cases.**

This is why asking questions matters when information is incomplete, such as a technical interview with no test cases. The interviewer may say many edge cases don't matter, but you can't be certain unless you ask.

## Why Create Test Cases Before the Algorithm or Code?

- **They force you to fully understand the requirements.** Coming up with inputs and predicting outputs sends you back to your requirements to make sure the definitions and rules are clear. If you can't build the test cases, something is missing from your requirement breakdown.
- **They expose gaps in the requirements.** Test cases are a more concrete version of the requirements. After writing one, you may realize its scenario isn't covered. Fixing requirements is much easier than fixing an algorithm, and especially code.
- **They give you runnable code to verify the solution.** They show which requirements your solution fails, which helps you debug and fix errors.
- **They give you an explicit stopping point.** Once they all pass, the solution is complete. This only holds if the test cases **fully cover all the requirements**. Gaps can make an incomplete or incorrect solution look finished.
- **They help in interviews and other situations with incomplete information.** You can ask the interviewer to verify your test cases. Ask **specific** questions: an interviewer may not answer "Have I covered all the edge cases?", but they can tell you whether your test cases are correct.
- **They show your thought process.** Writing test cases lets you communicate with the interviewer, and it gives them something positive to grade even if you don't finish a working solution.

## Common Mistakes

- **Thinking in terms of the solution** instead of the problem. Start with inputs, outputs, definitions, and rules.
- **Assuming what the input will be** without confirming with the interviewer. This can be a costly mistake.
- **Testing only one side of a conditional requirement.** Every "if" needs test cases for both sides.
- **Testing several requirements in one test case**, which makes failures harder to debug.
- **Trusting incomplete test cases.** If coverage has gaps, all tests can pass while the solution is still wrong.
- **Skipping test cases to save time in an interview.** It's easy to think you have a "working" solution, then realize it doesn't solve the right problem, when there may be no time left to start over.
