# JavaScript DOM Manipulation

## Explanation

The **DOM** (Document Object Model) is the browser's tree of objects representing a web page. JavaScript can read and change it to update the page without reloading.

Core tasks:

- **Select** elements: `document.querySelector(selector)` returns the first match (or `null`); `document.querySelectorAll(selector)` returns a static `NodeList`.
- **Change** elements: `textContent`, `classList`, `setAttribute`, `style`, `dataset`.
- **Create and insert**: `document.createElement`, `append`, `prepend`, `before`, `after`.
- **Remove**: `element.remove()`.
- **React to events**: `addEventListener(type, handler)`.

## Examples

```html
<ul id="todo-list"></ul>
<input id="todo-input" />
<button id="add-button">Add</button>
```

```javascript
const list = document.querySelector('#todo-list');
const input = document.querySelector('#todo-input');
const button = document.querySelector('#add-button');

button.addEventListener('click', () => {
  const text = input.value.trim();
  if (!text) return;

  const item = document.createElement('li');
  item.textContent = text; // safe: treats text as plain text
  item.classList.add('todo');
  list.append(item);

  input.value = '';
});
```

Event delegation: one listener on a parent handles events from many children, including ones added later.

```javascript
list.addEventListener('click', (event) => {
  const item = event.target.closest('li');
  if (item) {
    item.classList.toggle('done');
  }
});
```

Forms:

```javascript
form.addEventListener('submit', (event) => {
  event.preventDefault(); // stop the page from reloading
  const data = new FormData(form);
  console.log(data.get('email'));
});
```

## Common Mistakes

- Running scripts before the elements exist. Put `<script>` at the end of `<body>`, use `defer`, or wait for `DOMContentLoaded`.
- Not checking for `null` from `querySelector`, then getting `TypeError: Cannot read properties of null`.
- Using `innerHTML` with user input, which can allow cross-site scripting (XSS). Prefer `textContent`.
- Calling the handler instead of passing it: `addEventListener('click', handle())`.
- Expecting `querySelectorAll` to return an array. Use `forEach` on the `NodeList` or convert with `Array.from`.

## Edge Cases

- `getElementsByClassName` returns a live collection that updates as the DOM changes; `querySelectorAll` does not.
- Inside an arrow function handler, `this` is not the element; use `event.currentTarget`.
