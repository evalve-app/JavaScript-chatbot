# PEDAC Guided Practice: Leftover Blocks

## Explanation

This lesson solves a small programming problem step by step using the PEDAC process.

For each step, **do the task before reading the discussion**, and finish one step before moving on. Your notes, algorithm, and solution don't need to match the Launch School version. They should reflect how **you** approached each step. If you missed something in your initial exploration, think about why, and use that to improve your process.

## Examples

### The Problem: Leftover Blocks

You have a number of building blocks that can be used to build a valid structure. There are certain rules about what determines the validity of a structure:

- The building blocks are cubes
- The structure is built in layers
- The top layer is a single block
- A block in an upper layer must be supported by four blocks in a lower layer
- A block in a lower layer can support more than one block in an upper layer
- You cannot leave gaps between blocks

Write a program that, given the number for a specific amount of cubes, calculates the number of blocks left over after building the tallest possible valid structure.

### Test Cases

```javascript
console.log(calculateLeftoverBlocks(0) === 0); //true
console.log(calculateLeftoverBlocks(1) === 0); //true
console.log(calculateLeftoverBlocks(2) === 1); //true
console.log(calculateLeftoverBlocks(4) === 3); //true
console.log(calculateLeftoverBlocks(5) === 0); //true
console.log(calculateLeftoverBlocks(6) === 1); //true
console.log(calculateLeftoverBlocks(14) === 0); //true
```

## Step 1: Understand the Problem

**Tasks:**

- Make notes of your mental model for the problem, including explicit and implicit rules.
- Write a list of questions for anything that isn't clear from the description.

### Input / Output

The input and output are stated in the description:

```text
Input: integer for a specific amount of cubes
Output: integer for left over cubes after building tallest possible valid structure
```

### Explicit Rules

The description already lists explicit rules and links to a definition of a cube. Restate the explicit rules before trying to identify the implicit ones:

- Structures are built with blocks
- Blocks are cubes
- Cubes are six-sided, have square faces, and have equal lengths on all sides
- The top layer in the structure consists of a single block
- A block in an upper layer must be supported by four blocks in a lower layer
- A block in a lower layer can support more than one block in an upper layer
- Layers are solid structures – there are no gaps between blocks in a layer

Some are word for word from the description, and others are restated or taken from the cube definition. Producing a list like this from the problem description should be your goal.

### Implicit Rules

Implicit rules are trickier and require exploring the problem in more depth.

The description talks about the **validity of a structure**. Since structures are built in layers, layers can also be valid or invalid. That points to the core question: **how do we determine if a layer is valid?**

The last three explicit rules hold a clue:

- The first layer is always one block, and a block in an upper layer must be supported by four blocks below. So **the second layer contains (at least) four blocks**.
- If it contains only four, it's logical to arrange them in a **2x2 square** with the upper block centered above it.
- A block in a lower layer can support more than one block above, which suggests an **overlapping arrangement**. A sketch helps:

```text
    ---
  --- ---
--- --- ---
```

The middle block of the third layer supports two blocks in the second layer, which matches the rule. Extrapolating to 3D, the third layer is a **3x3 square of 9 blocks**. A pattern emerges:

```text
Layer 1: 1 block (1x1)
Layer 2: 4 blocks (2x2)
Layer 3: 9 blocks (3x3)
```

These are **square numbers**. Even if you don't recognize that, the pattern shows:

- There is a direct relationship between the layer number and the number of blocks along each side of that layer.
- The number of blocks in a layer is the number of blocks on one side multiplied by itself.

As implicit rules:

- Layer number correlates with blocks in a layer
- Layer number x Layer number = number of blocks in layer

### Questions

- **Is a lower layer still valid if it has more blocks than it needs?** A block in an upper layer needs four blocks below, but could layer two have five, six, or more? That would break the correlation between layer number and block count.
- **Will there always be left-over blocks?** The description says "calculates the number of blocks left over." Does that imply there will always be some?

How these are answered depends on context. In an interview you may be able to ask the interviewer. **If you have test cases, examine them first**, because they may answer your questions.

## Step 2: Examples and Test Cases

**Task:** With your mental model and questions from Step 1, make notes on the test cases. Do they confirm or refute parts of your analysis? Do they answer your questions or raise new ones?

Sometimes you have to create your own test cases, but in 110 and the 119 interview, you're given the ones you need. Besides verifying your solution, test cases help you **understand the problem and answer open questions**.

**Is a lower layer still valid if it has more blocks than it needs?**
**No**, based on the second-to-last test case. With 6 blocks, 5 are used (1 for the first layer, 4 for the second) and 1 is left over. If extra blocks could go in the second layer, 0 would be left over.

**Will there always be left-over blocks?**
**No.** The first, second, fifth, and last tests show 0 left over. If the input is the exact number of blocks needed for some number of valid layers, nothing is left over.

## Step 3: Data Structures

**Task:** Use your analysis so far to note whether you might need any particular data structures, and which ones.

For 110, and the Core Curriculum generally, you won't implement your own data structures. You'll use built-in ones such as **objects and arrays**. Sometimes exploring them at this step helps. Other times, how the data is structured isn't important to solving the problem at an abstract level and is more of an implementation detail.

For this problem, it's not clear yet whether a data structure is needed. We have to "build" an imaginary structure, but do we need to represent it as data? Make a note of the idea anyway:

- Perhaps use a nested array to represent the structure?
- Each subarray could represent a layer

```javascript
[
  ['x'],
  ['x', 'x', 'x', 'x'],
  ['x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x'],
  ...
]
```

It's always useful to note your thinking, even in a sentence or two. You can revisit and expand the idea later. **PEDAC is not a linear process.** Don't be afraid to move backward and forward between steps.

## Step 4: Algorithm

**Task:** Write a high-level algorithm that solves the problem at an abstract level. Avoid too much implementation detail.

### From Mental Model to Steps

**Imagine solving the problem by hand.** Here, imagine you actually have building blocks and are building a structure from some number of them to see how many are left. A logical approach:

1. Build the structure one layer at a time until you no longer have enough blocks left to build a "valid" layer.
2. Count how many blocks you have left.

That's a good start. Next, break it down further and describe it more **programmatically**, in terms of patterns like **loops and conditionals**. Don't think at the code level yet: avoid implementation details and specific programming languages.

Revisit the mental model:

- The smallest valid layer (the topmost layer) is one block.
- Layer 1 is a 1x1 square (1 block), layer 2 is a 2x2 square (4 blocks), and so on. If we track which layer number we're building, we can calculate the blocks it needs.

So start at the first layer, and for each additional layer, check whether enough blocks remain to build it. If so, build it. If not, return the remaining blocks.

### First Draft

```text
1. Start with:
    - A count of the 'blocks remaining' equal to the input
    - A count of the 'current layer' equal to 1

2. Subtract 1 from the 'blocks remaining' (to account for
   the block used in the first layer)

3. Calculate the number for the 'next layer' by adding 1 to
   the value for the 'current layer'

4. Using the number for the 'next layer', calculate the
   'blocks required' to build that layer, by multiplying the
   number by itself

5. Determine if the 'blocks remaining' is greater than or
   equal to the 'blocks required' to build the layer
    - If it is:
        - Subtract the 'blocks required' from the 'blocks
          remaining'
        - Increment the 'current layer' by 1
        - Go back to Step 3
    - If it isn't:
        - Return the 'blocks remaining'
```

### Test the Algorithm Against a Test Case

Walk through the first test case (input `0`):

- Step 1: 'blocks remaining' is 0, 'current layer' is 1
- Step 2: subtract 1 from 'blocks remaining' → **-1**
- Step 3: 'next layer' is 2 (1 + 1)
- Step 4: 'blocks required' is 2 x 2 = 4
- Step 5: 'blocks remaining' (-1) is less than 4, so return **-1**

The expected output is **0**, so the algorithm has a bug.

The problem shows up at step 2, but the underlying cause is that **step 2 exists at all**, because we start construction at layer 1. Options:

- Check first whether the input is 0, and if so, return 0 immediately.
- **Start at a theoretical "layer 0"** and remove step 2 altogether.

We'll use the second option.

### Adjusted Algorithm

```text
1. Start with:
    - A count of the 'blocks remaining' equal to the input
    - A count of the 'current layer' equal to 0

2. Calculate the number for the 'next layer' by adding 1 to
   the value for the 'current layer'

3. Using the number for the 'next layer', calculate the
   'blocks required' to build that layer, by multiplying the
   number by itself

4. Determine if the 'blocks remaining' is greater than or
   equal to the 'blocks required' to build the layer
    - If it is:
      - Subtract the 'blocks required' from 'blocks remaining'
      - Increment the 'current layer' by 1
      - Go back to Step 2
    - If it isn't:
      - Return 'blocks remaining'
```

### Re-Test the Algorithm

First test case (input `0`):

- Step 1: 'blocks remaining' is 0, 'current layer' is 0
- Step 2: 'next layer' is 1 (0 + 1)
- Step 3: 'blocks required' is 1 x 1 = 1
- Step 4: 'blocks remaining' (0) is less than 1, so return **0** ✓

Third test case (input `2`):

- Step 1: 'blocks remaining' is 2, 'current layer' is 0
- Step 2: 'next layer' is 1 (0 + 1)
- Step 3: 'blocks required' is 1 x 1 = 1
- Step 4: 'blocks remaining' (2) is greater than 1, so:
  - 'blocks remaining' = 2 - 1 = 1
  - 'current layer' = 0 + 1 = 1
- Step 2: 'next layer' is 2 (1 + 1)
- Step 3: 'blocks required' is 2 x 2 = 4
- Step 4: 'blocks remaining' (1) is less than 4, so return **1** ✓

You could run more test cases, but at this point we're confident enough to move on to implementation.

## Step 5: Implement a Solution in Code

**Task:** Implement a working solution in JavaScript that passes all the test cases.

### Implementation Notes

With a solid algorithm, it's tempting to start coding right away. But the algorithm is still fairly abstract, so it helps to make a few **implementation notes** first. You can:

- Edit the existing algorithm to add implementation detail,
- Write a separate implementation-specific version, or
- Make separate notes on how to approach the implementation.

The choice depends on personal preference and the problem. Here, the algorithm is already structured programmatically: **step 1 reads as variable initialization**, **steps 2 to 4 read as actions inside a loop**, and **step 4 reads as a conditional**. We don't need to rewrite it, but some aspects are worth noting.

**Which loop?** Step 4's condition ("blocks remaining is greater than or equal to blocks required") decides whether to iterate again. That fits a `while` loop:

- Use a while loop?
- For the condition, check if 'blocks remaining' is greater than or equal to the 'blocks required'

**Blocks for the next layer:** two steps can be combined into one calculation:

- The next layer's number is the current layer plus 1.
- Its block count is that number multiplied by itself, i.e., squared. JavaScript's `**` operator does this.

- Calculating the blocks for the next layer, use ** operator? e.g. (currentLayer + 1)**2

### Solution

```javascript
function calculateLeftoverBlocks(n) {
  let currentLayer = 0;
  let remainingCubes = n;

  let requiredCubes = (currentLayer + 1)**2;

  while (remainingCubes >= requiredCubes) {
    remainingCubes -= requiredCubes;
    currentLayer += 1;
    requiredCubes = (currentLayer + 1)**2;
  }

  return remainingCubes;
}
```

How the code maps to the algorithm:

- **Lines 2 and 3** (`currentLayer`, `remainingCubes`) → Step 1
- **Line 5** (`requiredCubes`) → Steps 2 and 3 combined
- **The `while` loop** → Step 4: it combines the conditional check and the iteration. The loop body does the incrementing, decrementing, and repeats steps 2 and 3.
- **Line 13** (`return remainingCubes`) → the "if it isn't" branch of Step 4, when the loop condition is no longer met

### Build Iteratively and Log Output

You generally wouldn't write the whole solution before running it. **Build it iteratively and run your code regularly.** Part of that is logging the values that change inside the `while` loop.

**Tip:** when logging multiple values, **wrap each variable in an object** so the output shows both the variable name and its value:

```javascript
// rest of function

while (remainingCubes >= requiredCubes) {
  remainingCubes -= requiredCubes;
  currentLayer += 1;
  requiredCubes = (currentLayer + 1)**2;
  console.log(
    {remainingCubes},
    {currentLayer},
    {requiredCubes}
  );
}

// {remainingCubes: 3} {currentLayer: 1} {requiredCubes: 4}
```

## Edge Cases

- **Zero blocks:** `calculateLeftoverBlocks(0)` returns `0`. The first-draft algorithm returned -1 here, which exposed the bug.
- **Exact fit, nothing left over:** inputs 1, 5, and 14 use every block (1, 1 + 4, 1 + 4 + 9).
- **Extra blocks can't widen a layer:** with 6 blocks, 1 is left over. A layer can't hold more blocks than it needs.
- **Not enough for the next layer:** with 4 blocks, only layer 1 is built and 3 are left over.

## Common Mistakes

- **Skipping implicit rules.** The square-number pattern isn't stated anywhere. You find it by exploring and sketching.
- **Asking questions before checking the test cases.** The test cases here answer both open questions.
- **Not walking through the algorithm with a test case.** Doing so with input `0` caught the -1 bug before any code was written.
- **Treating PEDAC as strictly linear.** It's fine to go back to earlier steps, such as revisiting the data structure idea.
- **Writing the complete solution before running any of it.** Build iteratively and log values as you go.
