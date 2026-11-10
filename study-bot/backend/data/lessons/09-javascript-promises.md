# JavaScript Promises

## Explanation

A **Promise** is an object that represents the eventual result of an asynchronous operation. A Promise is in one of three states:

- **pending**: not finished yet
- **fulfilled**: finished successfully with a value
- **rejected**: failed with a reason (usually an `Error`)

Once a Promise is fulfilled or rejected, it is **settled** and never changes again.

You react to a Promise with:

- `.then(onFulfilled)` for the value
- `.catch(onRejected)` for errors
- `.finally(onSettled)` for cleanup that runs either way

Each of these returns a new Promise, which allows chaining. Returning a value from `.then` passes it to the next `.then`; returning a Promise waits for it; throwing an error skips to the next `.catch`.

## Examples

```javascript
const roll = new Promise((resolve, reject) => {
  const value = Math.ceil(Math.random() * 6);
  if (value > 1) {
    resolve(value);
  } else {
    reject(new Error('Rolled a one'));
  }
});

roll
  .then((value) => value * 10)
  .then((points) => console.log(`Points: ${points}`))
  .catch((error) => console.error(error.message))
  .finally(() => console.log('Game over'));
```

Combining Promises:

```javascript
const fast = Promise.resolve('fast');
const slow = new Promise((resolve) => setTimeout(() => resolve('slow'), 100));

Promise.all([fast, slow]).then(console.log);        // ['fast', 'slow'] (rejects if any rejects)
Promise.allSettled([fast, Promise.reject(new Error('x'))]).then(console.log); // never rejects
Promise.race([fast, slow]).then(console.log);       // 'fast' (first to settle)
Promise.any([Promise.reject(new Error('a')), slow]).then(console.log); // 'slow' (first to fulfill)
```

## Common Mistakes

- Forgetting to `return` inside `.then`, which breaks the chain (the next `.then` gets `undefined`).
- Not adding a `.catch`, which causes "unhandled promise rejection" warnings.
- Wrapping an existing Promise in `new Promise(...)` unnecessarily.
- Expecting a Promise to give its value synchronously: `const data = fetch(url);` is a Promise, not data.
- Calling `resolve` and then continuing to run code you meant to skip; add `return`.

## Edge Cases

- `.then` callbacks always run asynchronously as microtasks, even if the Promise is already resolved.
- `Promise.all([])` resolves immediately with `[]`.
- Calling `resolve` or `reject` more than once has no effect after the first call.
