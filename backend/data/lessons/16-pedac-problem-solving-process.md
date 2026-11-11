# PEDAC Problem-Solving Process

## Explanation

**PEDAC** is Launch School's process for solving programming problems. It stands for:

- **P** – [Understand the] **Problem**
- **E** – **Examples** / Test Cases
- **D** – **Data Structure**
- **A** – **Algorithm**
- **C** – **Code**

PEDAC has two primary objectives:

- **Process the problem (PEDA).** Four steps take you from the problem statement to a solid understanding of what is required. The result is the **algorithm**.
- **Code with intent (C).** Convert the algorithm into the programming language of your choice. The result is the **implementation**.

PEDAC is one tool among many, not the only or best approach. You may not need it for every problem, but the more complex the problem, the more you need a rigorous process. It is especially useful for beginners who have never been forced to use a system of thinking, and it is a gateway to more formal algorithmic techniques.

### Why Use PEDAC?

For problems of a certain sophistication, PEDAC **saves time**. Going straight to coding is sometimes faster for simple problems. But the more complex the problem, the more likely that going straight to coding leads to **"hack and slash" coding**: code written without intent or context. Hack and slash code often fails to meet the requirements, misses edge cases, and is hard to understand, maintain, and scale.

Common pitfalls of hack and slash coding:

- Missed requirements
- Unforeseen edge cases
- Hard-to-understand code
- Code that's difficult to maintain

## Examples

The steps below all use this example problem:

> Suppose you have an arbitrary natural number (the **target**) and a set of one or more additional natural numbers (the **factors**). Write a program that computes the sum of all numbers from 1 up to the target number that are also multiples of one of the factors.
>
> For instance, if the target is 20, and the factors are 3 and 5, that gives us the list of multiples 3, 5, 6, 9, 10, 12, 15, 18. The sum of these multiples is 78.
>
> If no factors are given, use 3 and 5 as the default factors.

## Step 1: Understand the Problem (P)

It's tempting to jump into a REPL and start typing code. **Resist this temptation.** The first step is to digest the problem and get a holistic understanding of what it asks.

- **Read the problem statement carefully.** Most problem statements have no wasted words. Every word and detail matters.
- If you skip details, your brain fills in the gaps, and it may not fill them in correctly.

### Identify Inputs and Outputs

```text
inputs:
  target number
  the set of factors
output:
  sum of multiples
```

### Make Terms Explicit

Understand each term as it applies to the **problem domain**. This includes unfamiliar words and words with multiple meanings. For example, "balance" means different things in accounting and in supply chain.

This problem has a subtle implicit concept: **multiples**. Here, a multiple is "a number that can be divided by another number without a remainder." Normally you would seek clarification rather than assume a definition. The example confirms this one:

```text
target number:   20
multiples of 3:  3, 6, 9, 12, 15, 18  (no remainder when divided by 3)
multiples of 5:  5, 10, 15            (no remainder when divided by 5)
```

### Implicit Requirements

The problem conveys rules that are not stated directly:

- **The multiples must be unique.** 15 is a multiple of both 3 and 5, but it is added only once: 3 + 5 + 6 + 9 + 10 + 12 + 15 + 18 = 78. We learn this from the example, not from an explicit statement.
- **The target is the limit, but it is not a multiple to include.** 20 is a multiple of 5, but it is not in the sum.
- **All numbers are natural numbers.** Natural numbers start at 0 or 1 depending on the definition. Adding 0 doesn't change a sum, so it doesn't matter here. For simplicity, assume they start at 1.

### Clarifying Questions

Identify anything that needs clarification. Example questions and one set of possible answers:

- **What are the possible values for the target? Are negative numbers allowed?** Any natural number greater than 0. There will always be a target value.
- **How will the factors be provided?** As an array.
- **If only one factor is provided, should the program add 3 or 5 as a second factor?** No. Default to 3 and 5 only if no factors are provided.

Ask questions even if you think you understand the problem. It ensures you're solving the right problem.

### Mental Model (Optional)

A **mental model** is your summary view of the entire problem: what it requires, not how to solve it.

Mental model 1:

> Determine a list of all multiples of a set of factors up to a target value, then filter the list of multiples to the unique values. Finally, compute and return the sum of the unique multiples.

Mental model 2:

> Incrementally build a list of numbers that are multiples of a set of one or more factors. Add a multiple to the list only if it is not yet on the list. Finally, compute and return the sum of the numbers on the list.

There are multiple valid perspectives. You only need one model, as long as it fully and accurately captures the requirements.

## Step 2: Examples / Test Cases (E)

Come up with examples that **validate your understanding** of the problem. Confirmation usually comes from a person (ask them to confirm the output for an input) or from documentation of a process (follow it to check the output).

- Write examples as **tests** that show the expected output for given inputs.
- **Derive test cases from the rules** you identified in Step 1. Rules are an excellent source of test cases.
- Add test cases for **edge cases** (see Edge Cases below).

## Step 3: Data Structure (D)

Determine what data structures you will use to convert the input to the output. The chief considerations are your **programming language** and your **mental model**.

For the example problem, both mental models collect the multiples and then add them up. An **array** is a good fit for this collection. The models differ only in how and when they filter the numbers.

The data structure **influences the algorithm**, so the Data Structure and Algorithm steps are typically paired together.

## Step 4: Algorithm (A)

Write a series of instructions that transforms the input into the desired output.

- **Get the level of detail right.** It should be easy to convert to code without actually being code.
- **Don't write it at the programming-language level.** Languages offer several ways to achieve a result, and each can affect other parts of the program. Choosing an implementation too early means that if you later need a different one, you have to change both the code and the algorithm.
- **It's fine to change the algorithm** once coding starts. Two people solving the same problem often write different algorithms, especially with different mental models.
- **Test the algorithm manually** with your test cases before implementing it. You don't need every test case, just enough to be confident it works.

## Step 5: Code with Intent (C)

Implement the solution in your language of choice. Because of the work in the PEDA steps, implementation becomes a **simple translation** of the algorithm into syntax.

- Expect to **circle back** to the algorithm sometimes. You may have missed something. PEDAC minimizes those mistakes, so circling back is mostly fine-tuning.
- Either mental model works in either language, but the language can make one a better fit. Mental model 1 is slightly better suited to Ruby, which has a built-in method for returning the unique values in an array. JavaScript arrays do not.

## Edge Cases

**Edge cases** are inputs at the "edges" of the problem description that may be mishandled if you aren't careful.

- Problems that iterate over numbers have edge cases at one or both ends of the range.
- Typical edge cases: negative numbers, zero, and extremely high values (if performance matters).
- For collections, test with **zero, one, and multiple elements**.

The example problem has one significant edge case: **what if the last number before the target is a multiple of a factor?**

- With a target of 20 and factors 3 and 5, the last number added is 18, and 19 is correctly left out.
- But if 19 is one of the factors, 19 should be in the sum. It is the last number checked, right at the edge of the range, so you need a test case for it.

## Common Mistakes

- **Jumping straight into code.** On complex problems, this leads to hack and slash code that misses requirements and edge cases.
- **Skimming the problem statement.** Reading it like a magazine article lets your brain fill gaps incorrectly.
- **Assuming the meaning of domain terms.** Ask for clarification instead.
- **Missing implicit requirements.** Rules like "multiples must be unique" or "don't include the target" often appear only in the examples.
- **Writing the algorithm as code.** It locks in implementation choices too early.
- **Skipping the manual test of the algorithm** before coding it.
- **Saving PEDAC for only the hardest problems.** If your first use is on a very difficult problem, it's hard to get good at the process.

## Summary

You don't always need this much detail, and you don't need to follow the PEDA sequence strictly. The key ideas are to **process the problem** so you arrive at an algorithm, and then **code with intent**. It feels like a lot of work at first, but with practice PEDAC becomes fast and effective.

## FAQ

**What problems can I solve using PEDAC?**
Procedural coding problems, because PEDAC leads to a series of steps that produce a deterministic result. It isn't well suited to abstract tasks like "designing a UI."

**Should I use PEDAC even if the problem is small?**
If you haven't used a formal problem-solving process before, yes. Using it on trivial problems builds "muscle memory," so you can use it naturally on difficult problems, where you really need it.

**Can I use PEDAC for developing applications, not just coding problems?**
Yes, with some pre-work. Break the application down into smaller requirements until each has specific inputs and unambiguous outputs. PEDAC applies to any problem that meets that bar.
