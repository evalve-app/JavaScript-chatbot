# JavaScript Event Loop

## Explanation

JavaScript runs your code on a **single thread**: one piece of JavaScript runs at a time. The **event loop** is how it still handles timers, network responses, and user events without freezing.

The main parts:

- **Call stack**: the functions currently running. Synchronous code runs here until the stack is empty.
- **Web APIs / Node.js APIs**: the browser or Node.js handles timers, network requests, and I/O outside the JavaScript thread.
- **Task queue** (macrotask queue): callbacks from `setTimeout`, `setInterval`, I/O, and UI events wait here.
- **Microtask queue**: Promise callbacks (`.then`, `.catch`, `.finally`, code after `await`) and `queueMicrotask` callbacks wait here.

The loop, simplified:

1. Run the current task (for example, your script) until the call stack is empty.
2. Run **all** microtasks, including new microtasks added while running them.
3. Let the browser render if needed.
4. Take the next task from the task queue and repeat.

So microtasks always run before the next timer callback.

## Examples

```javascript
console.log('1: script start');

setTimeout(() => console.log('5: timeout'), 0);

Promise.resolve()
  .then(() => console.log('3: promise 1'))
  .then(() => console.log('4: promise 2'));

console.log('2: script end');

// Output order: 1, 2, 3, 4, 5
```

`await` splits a function: the code after it runs as a microtask.

```javascript
async function run() {
  console.log('A');
  await null;
  console.log('C');
}

run();
console.log('B');
// A, B, C
```

## Blocking the Loop

Long synchronous work blocks everything else, including clicks and rendering:

```javascript
const start = Date.now();
while (Date.now() - start < 3000) {} // page freezes for 3 seconds
```

Split heavy work into smaller pieces or move it to a Web Worker.

## Common Mistakes

- Expecting `setTimeout(fn, 0)` to run before Promise callbacks.
- Thinking the delay in `setTimeout` is exact. It is a minimum delay.
- Believing `async` code runs in parallel threads. It is concurrent, not parallel.

## Edge Cases

- A microtask that keeps scheduling microtasks can starve the task queue, so timers never run.
- Node.js has extra phases and `process.nextTick`, which runs before Promise microtasks.
