# JavaScript Async/Await

## Explanation

`async` and `await` are syntax for working with Promises in a top-to-bottom style.

- An `async` function **always returns a Promise**. Returning a value fulfills it; throwing an error rejects it.
- `await` pauses the `async` function until a Promise settles, then gives back its value (or throws its rejection reason).
- `await` only works inside `async` functions and at the top level of ES modules.

While an `async` function waits, other code keeps running. `await` does not block the whole program.

## Examples

```javascript
async function loadUser(id) {
  const response = await fetch(`https://api.example.com/users/${id}`);
  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}`);
  }
  return response.json();
}

async function main() {
  try {
    const user = await loadUser(1);
    console.log(user.name);
  } catch (error) {
    console.error('Could not load user:', error.message);
  }
}

main();
```

Running tasks in parallel instead of one after another:

```javascript
async function loadDashboard() {
  // Sequential: total time = time(a) + time(b)
  // const a = await getStats();
  // const b = await getNews();

  // Parallel: total time = the slower of the two
  const [stats, news] = await Promise.all([getStats(), getNews()]);
  return { stats, news };
}
```

## Common Mistakes

- **Forgetting `await`**: `const data = getData();` gives a pending Promise, not the data.
- Using `await` inside a non-`async` function, which is a `SyntaxError`.
- Using `await` inside `forEach`. `forEach` does not wait for the callbacks. Use `for...of` (sequential) or `Promise.all` with `map` (parallel).
- Forgetting that the caller of an `async` function also gets a Promise and must `await` it or use `.then`.
- Missing `try...catch`, so rejections go unhandled.

```javascript
// Bug: logs before the saves finish
items.forEach(async (item) => {
  await save(item);
});
console.log('All saved?');

// Fix
for (const item of items) {
  await save(item);
}
console.log('All saved');
```

## Edge Cases

- `return await promise` inside `try` lets the `catch` handle that rejection; plain `return promise` does not.
- `await` on a non-Promise value just returns the value (after a microtask).
